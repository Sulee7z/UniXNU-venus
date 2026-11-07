#include <kern/kalloc.h>
extern int native_ram_block_gpu_addon(const uint8_t **, uint64_t *) __attribute__((weak_import));
#include <libkern/zlib.h>
/* zlib's state, from kalloc with its size in front (the default allocator of the kernel's zlib is not meant for this). */
static voidpf
native_gpu_addon_zalloc(voidpf opaque __unused, uInt items, uInt size)
{
	size_t bytes = (size_t)items * size + 16;
	uint8_t *block = kalloc_data(bytes, Z_WAITOK | Z_ZERO);
	if (!block) {
		return Z_NULL;
	}
	memcpy(block, &bytes, sizeof(bytes));
	return block + 16;
}
static void
native_gpu_addon_zfree(voidpf opaque __unused, voidpf address)
{
	uint8_t *block = (uint8_t *)address - 16;
	size_t bytes = 0;
	memcpy(&bytes, block, sizeof(bytes));
	kfree_data(block, bytes);
}
static int
native_gpu_addon_inflate(const uint8_t *packed, uint64_t packed_size, uint8_t *data, uint64_t size)
{
	z_stream stream;
	memset(&stream, 0, sizeof(stream));
	stream.zalloc = native_gpu_addon_zalloc;
	stream.zfree = native_gpu_addon_zfree;
	stream.next_in = (Bytef *)(uintptr_t)packed;
	stream.avail_in = (uInt)packed_size;
	stream.next_out = data;
	stream.avail_out = (uInt)(size ? size : 1);
	if (inflateInit(&stream) != Z_OK) {
		return ENOMEM;
	}
	int result = inflate(&stream, Z_FINISH);
	inflateEnd(&stream);
	return result == Z_STREAM_END && stream.total_out == size && !stream.avail_in ? 0 : EINVAL;
}
volatile int native_gpu_addon_files = -1;
volatile int native_gpu_addon_written = 0;
volatile int native_gpu_addon_same = 0;
volatile int native_gpu_addon_failed = 0;
volatile int native_gpu_addon_error = 0;
static int
native_gpu_addon_equal(vnode_t vp, const uint8_t *data, uint64_t size, uint32_t mode, vfs_context_t ctx)
{
	struct vnode_attr va;
	VATTR_INIT(&va);
	VATTR_WANTED(&va, va_data_size);
	VATTR_WANTED(&va, va_mode);
	if (vnode_getattr(vp, &va, ctx) || va.va_data_size != size || (va.va_mode & 07777) != mode) {
		return 0;
	}
	const uint32_t chunk = 1024 * 1024;
	uint8_t *buffer = kalloc_data(chunk, Z_WAITOK);
	if (!buffer) {
		return 0;
	}
	int equal = 1;
	for (uint64_t at = 0; equal && at < size; at += chunk) {
		int length = (int)(size - at < chunk ? size - at : chunk), resid = 0;
		if (vn_rdwr(UIO_READ, vp, (caddr_t)buffer, length, (off_t)at, UIO_SYSSPACE, IO_NOAUTH, vfs_context_ucred(ctx), &resid,
		    vfs_context_proc(ctx)) || resid || memcmp(buffer, data + at, length)) {
			equal = 0;
		}
	}
	kfree_data(buffer, chunk);
	return equal;
}
static int
native_gpu_addon_write(const char *path, const uint8_t *data, uint64_t size, uint32_t mode, vfs_context_t ctx)
{
	vnode_t vp = NULLVP;
	int error = vnode_open(path, FREAD | O_NOFOLLOW, 0, 0, &vp, ctx);
	if (!error) {
		int equal = native_gpu_addon_equal(vp, data, size, mode, ctx);
		vnode_close(vp, FREAD, ctx);
		vp = NULLVP;
		if (equal) {
			return -1;
		}
	}
	error = vnode_open(path, O_CREAT | O_TRUNC | FWRITE | O_NOFOLLOW, mode, 0, &vp, ctx);
	if (error) {
		return error;
	}
	int resid = 0;
	error = vn_rdwr(UIO_WRITE, vp, (caddr_t)(uintptr_t)data, (int)size, 0, UIO_SYSSPACE, IO_NOAUTH | IO_UNIT, vfs_context_ucred(ctx),
	    &resid, vfs_context_proc(ctx));
	if (!error && resid) {
		error = EIO;
	}
	if (!error) {
		struct vnode_attr va;
		VATTR_INIT(&va);
		VATTR_SET(&va, va_mode, mode);
		error = vnode_setattr(vp, &va, ctx);
	}
	if (!error) {
		error = VNOP_FSYNC(vp, MNT_WAIT, ctx);
	}
	int close_error = vnode_close(vp, FWRITE, ctx);
	return error ? error : close_error;
}
/* Creates the missing parent directories of an addon path with the mkdir syscall, /private/var/ngpu itself included (a Data seed
 * that never had add-gpu-plugin-data.py applied has none). The scratch is one 4 KiB page; the mount arguments end below 0xa00. */
static int
native_gpu_addon_parents(proc_t p, user_addr_t scratch, const char *path)
{
	char parent[MAXPATHLEN];
	if (strlcpy(parent, path, sizeof(parent)) >= sizeof(parent)) return ENAMETOOLONG;
	for (size_t i = sizeof("/private/var/ngpu") - 1; parent[i]; ++i) {
		if (parent[i] != '/') {
			continue;
		}
		parent[i] = 0;
		struct mkdir_args request = {.path = scratch + 0xc00, .mode = 0755};
		int32_t result = 0;
		int error = copyout(parent, request.path, i + 1);
		if (!error) {
			error = mkdir(p, &request, &result);
		}
		parent[i] = '/';
		if (error && error != EEXIST) {
			return error;
		}
	}
	return 0;
}
static void
native_gpu_addon_install(proc_t p, user_addr_t scratch)
{
	const uint8_t *addon = NULL;
	uint64_t bytes = 0;
	if (!native_ram_block_gpu_addon || !native_ram_block_gpu_addon(&addon, &bytes)) {
		return;
	}
	uint32_t count = 0;
	uint64_t total = 0;
	if (bytes < 24 || memcmp(addon, "NGPUADD2", 8)) {
		native_gpu_addon_error = EINVAL;
		return;
	}
	memcpy(&count, addon + 8, 4);
	memcpy(&total, addon + 16, 8);
	if (total != bytes || !count || count > 4096) {
		native_gpu_addon_error = EINVAL;
		return;
	}
	/* Validate the whole addon before writing anything. */
	uint64_t at = 24;
	for (uint32_t i = 0; i < count; ++i) {
		uint32_t name_bytes = 0, mode = 0;
		uint64_t size = 0, packed = 0;
		if (bytes - at < 24) {
			native_gpu_addon_error = EINVAL;
			return;
		}
		memcpy(&name_bytes, addon + at, 4);
		memcpy(&mode, addon + at + 4, 4);
		memcpy(&size, addon + at + 8, 8);
		memcpy(&packed, addon + at + 16, 8);
		at += 24;
		uint64_t name_padded = (name_bytes + 7) & ~7ULL, size_padded = (packed + 7) & ~7ULL;
		const char *name = (const char *)(addon + at);
		if (name_bytes < 2 || name_bytes > 240 || bytes - at < name_padded || name[name_bytes - 1] || strnlen(name, name_bytes) != name_bytes - 1 ||
		    name[0] == '/' || strncmp(name, "systemos49/", 11) || (mode & ~0777) || size > INT32_MAX || !packed || packed > INT32_MAX || bytes - at - name_padded < size_padded) {
			native_gpu_addon_error = EINVAL;
			return;
		}
		for (uint32_t k = 0; k + 1 < name_bytes - 1; ++k) {
			if (name[k] == '.' && name[k + 1] == '.') {
				native_gpu_addon_error = EINVAL;
				return;
			}
		}
		at += name_padded + size_padded;
	}
	if (at != bytes) {
		native_gpu_addon_error = EINVAL;
		return;
	}
	native_gpu_addon_files = (int)count;
	vfs_context_t ctx = vfs_context_current();
	char path[MAXPATHLEN];
	at = 24;
	for (uint32_t i = 0; i < count; ++i) {
		uint32_t name_bytes = 0, mode = 0;
		uint64_t size = 0, packed = 0;
		memcpy(&name_bytes, addon + at, 4);
		memcpy(&mode, addon + at + 4, 4);
		memcpy(&size, addon + at + 8, 8);
		memcpy(&packed, addon + at + 16, 8);
		at += 24;
		const char *name = (const char *)(addon + at);
		at += (name_bytes + 7) & ~7ULL;
		snprintf(path, sizeof(path), "/private/var/ngpu/%s", name);
		uint8_t *data = kalloc_data(size ? size : 1, Z_WAITOK);
		int error = data ? native_gpu_addon_inflate(addon + at, packed, data, size) : ENOMEM;
		if (!error) {
			error = native_gpu_addon_write(path, data, size, mode, ctx);
			if (error == ENOENT && !(error = native_gpu_addon_parents(p, scratch, path))) {
				error = native_gpu_addon_write(path, data, size, mode, ctx);
			}
		}
		if (data) {
			kfree_data(data, size ? size : 1);
		}
		if (error < 0) {
			native_gpu_addon_same++;
		} else if (error) {
			native_gpu_addon_failed++;
			native_gpu_addon_error = error;
		} else {
			native_gpu_addon_written++;
		}
		at += (packed + 7) & ~7ULL;
	}
}

/* SystemOS composition follows zeta32f3024, but stays in RAM instead of rewriting
 * the installed root. Only /System and /usr are readonly union views; the two
 * original dyld cache directories were excluded from the source artifact. */
volatile int venus_systemos049_stage = 0;
volatile int venus_systemos049_status = -1;
volatile int venus_systemos049_cache_preserved = 0;
static int
venus_systemos049_bind(proc_t p, user_addr_t scratch, const char *source, const char *point, int flags)
{
    struct mount_args request = {.type = scratch + 0xa00, .path = scratch + 0xa20,
        .flags = MNT_RDONLY | flags, .data = scratch + 0xb00};
    int32_t result = 0;
    int error = copyout("bindfs", request.type, 7);
    if (!error) error = copyout(point, request.path, strlen(point) + 1);
    if (!error) error = copyout(source, request.data, strlen(source) + 1);
    if (error) return error;
    native_bindfs_boot_mount = 1;
    error = mount(p, &request, &result);
    native_bindfs_boot_mount = 0;
    printf("SystemOS049: bind source=%s point=%s flags=0x%x error=%d\n", source, point, request.flags, error);
    return error;
}
static int
venus_systemos049_prepare(proc_t p, user_addr_t scratch)
{
    uint32_t enabled = 0, persist = 0;
    if (!PE_parse_boot_argn("venus-systemos-view", &enabled, sizeof(enabled)) || enabled != 1) return 0;
    if (!PE_parse_boot_argn("sheng-data-persist", &persist, sizeof(persist)) || persist != 1 || native_owner_data_stage != 4) return EPERM;
    vfs_context_t ctx = vfs_context_current();
    vnode_t cache_before = NULLVP, cache_after = NULLVP, library = NULLVP;
    const char *cache = "/System/Library/Caches/com.apple.dyld";
    int error = vnode_lookup(cache, 0, &cache_before, ctx);
    if (error) return error;
    mount_t original_cache_mount = vnode_mount(cache_before);
    venus_systemos049_stage = 1;
    native_gpu_addon_install(p, scratch);
    printf("SystemOS049: installer files=%d written=%d same=%d failed=%d error=%d\n",
        native_gpu_addon_files, native_gpu_addon_written, native_gpu_addon_same,
        native_gpu_addon_failed, native_gpu_addon_error);
    if (native_gpu_addon_files < 1 || native_gpu_addon_failed || native_gpu_addon_error) {
        error = native_gpu_addon_error ? native_gpu_addon_error : ENOENT;
        goto done;
    }
    venus_systemos049_stage = 2;
    error = venus_systemos049_bind(p, scratch, "/private/var/ngpu/systemos49/System", "/System", MNT_UNION);
    if (error) goto done;
    venus_systemos049_stage = 3;
    error = venus_systemos049_bind(p, scratch, "/private/var/ngpu/systemos49/usr", "/usr", MNT_UNION);
    if (error) goto done;
    venus_systemos049_stage = 4;
    error = vnode_lookup(cache, 0, &cache_after, ctx);
    if (error) goto done;
    if (vnode_mount(cache_after) != original_cache_mount) { error = EAUTH; goto done; }
    venus_systemos049_cache_preserved = 1;
    error = vnode_lookup("/usr/lib/libobjc-trampolines.dylib", 0, &library, ctx);
    if (error) goto done;
    venus_systemos049_stage = 5;
    error = native_gpu_addon_parents(p, scratch, "/private/var/ngpu/preboot/Cryptexes/OS/System/");
    if (!error) error = native_gpu_addon_parents(p, scratch, "/private/var/ngpu/preboot/Cryptexes/OS/usr/");
    if (error) goto done;
    error = venus_systemos049_bind(p, scratch, "/private/var/ngpu/preboot", "/private/preboot", MNT_UNION);
    if (error) goto done;
    error = venus_systemos049_bind(p, scratch, "/private/var/ngpu/systemos49/System", "/private/preboot/Cryptexes/OS/System", 0);
    if (error) goto done;
    error = venus_systemos049_bind(p, scratch, "/private/var/ngpu/systemos49/usr", "/private/preboot/Cryptexes/OS/usr", 0);
    if (error) goto done;
    venus_systemos049_stage = 6;
done:
    if (library) vnode_put(library);
    if (cache_after) vnode_put(cache_after);
    if (cache_before) vnode_put(cache_before);
    venus_systemos049_status = error;
    printf("SystemOS049: prepare stage=%d status=%d cache-preserved=%d\n",
        venus_systemos049_stage, error, venus_systemos049_cache_preserved);
    return error;
}
