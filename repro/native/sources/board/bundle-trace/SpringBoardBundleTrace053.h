/* Read-only observation of the exact23F84 cached system bundle identifier.
 * Preserve the original abort, privacy, signature and application decisions. */
#include <pexpert/pexpert.h>

static void
venus_springboard_bundle053(mach_vm_offset_t cache)
{
	unsigned enabled = 0;
	proc_t process = get_bsdtask_info(current_task());
	if (process == NULL || strcmp(proc_name_address(process), "SpringBoard") != 0 ||
	    !PE_parse_boot_argn("venus-sb-info", &enabled, sizeof(enabled)) || enabled != 1) {
		return;
	}
	/* Original cache region and FrontBoard dispatch-once result slot, pinned to23F84. */
	const uint64_t original_base = UINT64_C(0x180000000);
	const uint64_t original_slot = UINT64_C(0x1ea4c0a28);
	if (cache < original_base || cache - original_base > UINT64_C(0x100000000)) {
		printf("SB053: pid=%d invalid cache base 0x%llx\n", proc_pid(process), (uint64_t)cache);
		return;
	}
	uint64_t identifier = 0, words[4] = {0};
	uint64_t address = original_slot + cache - original_base;
	int error = copyin((user_addr_t)address, &identifier, sizeof(identifier));
	printf("SB053: pid=%d cache=0x%llx identifier-slot=0x%llx read=%d identifier=0x%llx\n",
	    proc_pid(process), (uint64_t)cache, address, error, identifier);
	if (!error && identifier >= UINT64_C(0x100000000) && identifier < UINT64_C(0x8000000000)) {
		error = copyin((user_addr_t)identifier, words, sizeof(words));
		printf("SB053: identifier object read=%d words=0x%llx/0x%llx/0x%llx/0x%llx\n",
		    error, words[0], words[1], words[2], words[3]);
	}
}
