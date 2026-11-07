#ifndef	_vm32_map_server_
#define	_vm32_map_server_

/* Module vm32_map */

#include <string.h>
#include <mach/ndr.h>
#include <mach/boolean.h>
#include <mach/kern_return.h>
#include <mach/notify.h>
#include <mach/mach_types.h>
#include <mach/message.h>
#include <mach/mig_errors.h>
#include <mach/port.h>
	
/* BEGIN MIG_STRNCPY_ZEROFILL CODE */

#if defined(__has_include)
#if __has_include(<mach/mig_strncpy_zerofill_support.h>)
#ifndef USING_MIG_STRNCPY_ZEROFILL
#define USING_MIG_STRNCPY_ZEROFILL
#endif
#ifndef __MIG_STRNCPY_ZEROFILL_FORWARD_TYPE_DECLS__
#define __MIG_STRNCPY_ZEROFILL_FORWARD_TYPE_DECLS__
#ifdef __cplusplus
extern "C" {
#endif
#ifndef __MIG_STRNCPY_ZEROFILL_FORWARD_TYPE_DECLS_CSTRING_ATTR
#define __MIG_STRNCPY_ZEROFILL_FORWARD_TYPE_DECLS_CSTRING_COUNTEDBY_ATTR(C) __unsafe_indexable
#endif
	extern int mig_strncpy_zerofill(char * dest, const char * src, int len) __attribute__((weak_import));
#ifdef __cplusplus
}
#endif
#endif /* __MIG_STRNCPY_ZEROFILL_FORWARD_TYPE_DECLS__ */
#endif /* __has_include(<mach/mig_strncpy_zerofill_support.h>) */
#endif /* __has_include */
	
/* END MIG_STRNCPY_ZEROFILL CODE */


#ifdef AUTOTEST
#ifndef FUNCTION_PTR_T
#define FUNCTION_PTR_T
typedef void (*function_ptr_t)(mach_port_t, char *, mach_msg_type_number_t);
typedef struct {
        char            * name;
        function_ptr_t  function;
} function_table_entry;
typedef function_table_entry   *function_table_t;
#endif /* FUNCTION_PTR_T */
#endif /* AUTOTEST */

#ifndef	vm32_map_MSG_COUNT
#define	vm32_map_MSG_COUNT	34
#endif	/* vm32_map_MSG_COUNT */

#include <Availability.h>
#include <mach/std_types.h>
#include <mach/mig.h>
#include <ipc/ipc_voucher.h>
#include <kern/ipc_kobject.h>
#include <kern/ipc_tt.h>
#include <kern/ipc_host.h>
#include <kern/ledger.h>
#include <kern/processor.h>
#include <kern/sync_sema.h>
#include <ipc/ipc_eventlink.h>
#include <vm/memory_object.h>
#include <vm/vm_map.h>
#include <kern/ipc_mig.h>
#include <kern/task_ident.h>
#include <kern/kern_cdata.h>
#include <mach/mig.h>
#include <mach/mach_types.h>
#include <mach_debug/mach_debug_types.h>

#ifdef __BeforeMigServerHeader
__BeforeMigServerHeader
#endif /* __BeforeMigServerHeader */

#ifndef MIG_SERVER_ROUTINE
#define MIG_SERVER_ROUTINE
#endif


/* Routine vm32_vm_region */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_region
(
	vm_map_read_t target_task,
	vm32_address_ut *address,
	vm32_size_ut *size,
	vm_region_flavor_t flavor,
	vm_region_info_t info,
	mach_msg_type_number_t *infoCnt,
	mach_port_t *object_name
);

/* Routine vm32_vm_allocate */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_allocate
(
	vm_map_t target_task,
	vm32_address_ut *address,
	vm32_size_ut size,
	int flags
);

/* Routine vm32_vm_deallocate */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_deallocate
(
	vm_map_t target_task,
	vm32_address_ut address,
	vm32_size_ut size
);

/* Routine vm32_vm_protect */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_protect
(
	vm_map_t target_task,
	vm32_address_ut address,
	vm32_size_ut size,
	boolean_t set_maximum,
	vm_prot_ut new_protection
);

/* Routine vm32_vm_inherit */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_inherit
(
	vm_map_t target_task,
	vm32_address_ut address,
	vm32_size_ut size,
	vm_inherit_ut new_inheritance
);

/* Routine vm32_vm_read */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_read
(
	vm_map_read_t target_task,
	vm32_address_ut address,
	vm32_size_ut size,
	pointer_ut *data,
	mach_msg_type_number_t *dataCnt
);

/* Routine vm32_vm_read_list */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_read_list
(
	vm_map_read_t target_task,
	vm32_read_entry_t data_list,
	natural_t count
);

/* Routine vm32_vm_write */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_write
(
	vm_map_t target_task,
	vm32_address_ut address,
	pointer_ut data,
	mach_msg_type_number_t dataCnt
);

/* Routine vm32_vm_copy */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_copy
(
	vm_map_t target_task,
	vm32_address_ut source_address,
	vm32_size_ut size,
	vm32_address_ut dest_address
);

/* Routine vm32_vm_read_overwrite */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_read_overwrite
(
	vm_map_read_t target_task,
	vm32_address_ut address,
	vm32_size_ut size,
	vm32_address_ut data,
	vm32_size_ut *outsize
);

/* Routine vm32_vm_msync */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_msync
(
	vm_map_t target_task,
	vm32_address_ut address,
	vm32_size_ut size,
	vm_sync_t sync_flags
);

/* Routine vm32_vm_behavior_set */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_behavior_set
(
	vm_map_t target_task,
	vm32_address_ut address,
	vm32_size_ut size,
	vm_behavior_ut new_behavior
);

/* Routine vm32_vm_map */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_map
(
	vm_map_t target_task,
	vm32_address_ut *address,
	vm32_size_ut size,
	vm32_address_ut mask,
	int flags,
	mem_entry_name_port_t object,
	vm32_offset_ut offset,
	boolean_t copy,
	vm_prot_ut cur_protection,
	vm_prot_ut max_protection,
	vm_inherit_ut inheritance
);

/* Routine vm32_vm_machine_attribute */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_machine_attribute
(
	vm_map_t target_task,
	vm32_address_ut address,
	vm32_size_ut size,
	vm_machine_attribute_t attribute,
	vm_machine_attribute_val_t *value
);

/* Routine vm32_vm_remap */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_remap
(
	vm_map_t target_task,
	vm32_address_ut *target_address,
	vm32_size_ut size,
	vm32_address_ut mask,
	boolean_t anywhere,
	vm_map_t src_task,
	vm32_address_ut src_address,
	boolean_t copy,
	vm_prot_ut *cur_protection,
	vm_prot_ut *max_protection,
	vm_inherit_ut inheritance
);

/* Routine vm32_task_wire */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_task_wire
(
	vm_map_t target_task,
	boolean_t must_wire
);

/* Routine vm32_mach_make_memory_entry */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_mach_make_memory_entry
(
	vm_map_t target_task,
	vm32_size_ut *size,
	vm32_offset_ut offset,
	vm_prot_ut permission,
	mem_entry_name_port_t *object_handle,
	mem_entry_name_port_t parent_entry
);

/* Routine vm32_vm_map_page_query */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_map_page_query
(
	vm_map_read_t target_map,
	vm32_offset_ut offset,
	integer_t *disposition,
	integer_t *ref_count
);

/* Routine vm32_mach_vm_region_info */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_mach_vm_region_info
(
	vm_map_read_t task,
	vm32_address_ut address,
	vm_info_region_t *region,
	vm_info_object_array_t *objects,
	mach_msg_type_number_t *objectsCnt
);

/* Routine vm32_vm_mapped_pages_info */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_mapped_pages_info
(
	vm_map_read_t task,
	page_address_array_t *pages,
	mach_msg_type_number_t *pagesCnt
);

/* Routine vm32_vm_region_recurse */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_region_recurse
(
	vm_map_read_t target_task,
	vm32_address_ut *address,
	vm32_size_ut *size,
	natural_t *nesting_depth,
	vm_region_recurse_info_t info,
	mach_msg_type_number_t *infoCnt
);

/* Routine vm32_vm_region_recurse_64 */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_region_recurse_64
(
	vm_map_read_t target_task,
	vm32_address_ut *address,
	vm32_size_ut *size,
	natural_t *nesting_depth,
	vm_region_recurse_info_t info,
	mach_msg_type_number_t *infoCnt
);

/* Routine vm32_mach_vm_region_info_64 */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_mach_vm_region_info_64
(
	vm_map_read_t task,
	vm32_address_ut address,
	vm_info_region_64_t *region,
	vm_info_object_array_t *objects,
	mach_msg_type_number_t *objectsCnt
);

/* Routine vm32_vm_region_64 */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_region_64
(
	vm_map_read_t target_task,
	vm32_address_ut *address,
	vm32_size_ut *size,
	vm_region_flavor_t flavor,
	vm_region_info_t info,
	mach_msg_type_number_t *infoCnt,
	mach_port_t *object_name
);

/* Routine vm32_mach_make_memory_entry_64 */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_mach_make_memory_entry_64
(
	vm_map_t target_task,
	memory_object_size_ut *size,
	memory_object_offset_ut offset,
	vm_prot_ut permission,
	mach_port_t *object_handle,
	mem_entry_name_port_t parent_entry
);

/* Routine vm32_vm_map_64 */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_map_64
(
	vm_map_t target_task,
	vm32_address_ut *address,
	vm32_size_ut size,
	vm32_address_ut mask,
	int flags,
	mem_entry_name_port_t object,
	memory_object_offset_ut offset,
	boolean_t copy,
	vm_prot_ut cur_protection,
	vm_prot_ut max_protection,
	vm_inherit_ut inheritance
);

/* Routine vm32_vm_purgable_control */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_purgable_control
(
	vm_map_t target_task,
	vm32_address_ut address,
	vm_purgable_t control,
	int *state
);

/* Routine vm32_vm_map_exec_lockdown */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_map_exec_lockdown
(
	vm_map_t target_task
);

/* Routine vm32_vm_reallocate */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t vm32_vm_reallocate
(
	vm_map_t target_task,
	vm32_address_ut src,
	vm32_size_ut src_size,
	vm32_address_ut *dst,
	vm32_size_ut dst_size,
	vm32_offset_ut align_mask,
	int options,
	int flags
);

#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
boolean_t vm32_map_server(
		mach_msg_header_t *InHeadP,
		void *InDataP,
		mach_msg_max_trailer_t *InTrailerP,
		mach_msg_header_t *OutHeadP,
		void *OutDataP);

#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
mig_kern_routine_t vm32_map_server_routine(
		mach_msg_header_t *InHeadP);


/* Description of this kernel subsystem, for use in direct RPC */
extern const struct vm32_map_subsystem {
	mig_kern_server_routine_t	kserver;	/* Server routine */
	mach_msg_id_t	start;	/* Min routine number */
	mach_msg_id_t	end;	/* Max routine number + 1 */
	unsigned int	maxsize;	/* Max msg size */
	vm_address_t	reserved;	/* Reserved */
	struct kern_routine_descriptor	/* Array of routine descriptors */
		kroutine[34];
} vm32_map_subsystem;

/* typedefs for all requests */

#ifndef __Request__vm32_map_subsystem__defined
#define __Request__vm32_map_subsystem__defined

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		vm_region_flavor_t flavor;
		mach_msg_type_number_t infoCnt;
	} __Request__vm32_vm_region_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_region_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm_region_flavor_t flavor;
		mach_msg_type_number_t infoCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_region_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		int flags;
	} __Request__vm32_vm_allocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_allocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		int flags;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_allocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
	} __Request__vm32_vm_deallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_deallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_deallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		boolean_t set_maximum;
		vm_prot_ut new_protection;
	} __Request__vm32_vm_protect_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_protect_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		boolean_t set_maximum;
		vm_prot_ut new_protection;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_protect_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm_inherit_ut new_inheritance;
	} __Request__vm32_vm_inherit_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_inherit_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm_inherit_ut new_inheritance;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_inherit_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
	} __Request__vm32_vm_read_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_read_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_read_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_read_entry_t data_list;
		natural_t count;
	} __Request__vm32_vm_read_list_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_read_list_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_read_entry_t data_list;
		natural_t count;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_read_list_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_ool_descriptor_t data;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		vm32_address_ut address;
		mach_msg_type_number_t dataCnt;
	} __Request__vm32_vm_write_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_ool_descriptor_t data;
	} __RequestKData__vm32_vm_write_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		mach_msg_type_number_t dataCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_write_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut source_address;
		vm32_size_ut size;
		vm32_address_ut dest_address;
	} __Request__vm32_vm_copy_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_copy_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut source_address;
		vm32_size_ut size;
		vm32_address_ut dest_address;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_copy_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm32_address_ut data;
	} __Request__vm32_vm_read_overwrite_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_read_overwrite_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm32_address_ut data;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_read_overwrite_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm_sync_t sync_flags;
	} __Request__vm32_vm_msync_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_msync_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm_sync_t sync_flags;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_msync_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm_behavior_ut new_behavior;
	} __Request__vm32_vm_behavior_set_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_behavior_set_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm_behavior_ut new_behavior;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_behavior_set_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t object;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm32_address_ut mask;
		int flags;
		vm32_offset_ut offset;
		boolean_t copy;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
		vm_inherit_ut inheritance;
	} __Request__vm32_vm_map_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t object;
	} __RequestKData__vm32_vm_map_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm32_address_ut mask;
		int flags;
		vm32_offset_ut offset;
		boolean_t copy;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
		vm_inherit_ut inheritance;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_map_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm_machine_attribute_t attribute;
		vm_machine_attribute_val_t value;
	} __Request__vm32_vm_machine_attribute_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_machine_attribute_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm_machine_attribute_t attribute;
		vm_machine_attribute_val_t value;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_machine_attribute_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t src_task;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		vm32_address_ut target_address;
		vm32_size_ut size;
		vm32_address_ut mask;
		boolean_t anywhere;
		vm32_address_ut src_address;
		boolean_t copy;
		vm_inherit_ut inheritance;
	} __Request__vm32_vm_remap_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t src_task;
	} __RequestKData__vm32_vm_remap_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut target_address;
		vm32_size_ut size;
		vm32_address_ut mask;
		boolean_t anywhere;
		vm32_address_ut src_address;
		boolean_t copy;
		vm_inherit_ut inheritance;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_remap_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		boolean_t must_wire;
	} __Request__vm32_task_wire_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_task_wire_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		boolean_t must_wire;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_task_wire_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t parent_entry;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		vm32_size_ut size;
		vm32_offset_ut offset;
		vm_prot_ut permission;
	} __Request__vm32_mach_make_memory_entry_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t parent_entry;
	} __RequestKData__vm32_mach_make_memory_entry_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_size_ut size;
		vm32_offset_ut offset;
		vm_prot_ut permission;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_mach_make_memory_entry_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_offset_ut offset;
	} __Request__vm32_vm_map_page_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_map_page_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_offset_ut offset;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_map_page_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
	} __Request__vm32_mach_vm_region_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_mach_vm_region_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_mach_vm_region_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __Request__vm32_vm_mapped_pages_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_mapped_pages_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_mapped_pages_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		natural_t nesting_depth;
		mach_msg_type_number_t infoCnt;
	} __Request__vm32_vm_region_recurse_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_region_recurse_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		natural_t nesting_depth;
		mach_msg_type_number_t infoCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_region_recurse_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		natural_t nesting_depth;
		mach_msg_type_number_t infoCnt;
	} __Request__vm32_vm_region_recurse_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_region_recurse_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		natural_t nesting_depth;
		mach_msg_type_number_t infoCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_region_recurse_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
	} __Request__vm32_mach_vm_region_info_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_mach_vm_region_info_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_mach_vm_region_info_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		vm_region_flavor_t flavor;
		mach_msg_type_number_t infoCnt;
	} __Request__vm32_vm_region_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_region_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm_region_flavor_t flavor;
		mach_msg_type_number_t infoCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_region_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t parent_entry;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		memory_object_size_ut size;
		memory_object_offset_ut offset;
		vm_prot_ut permission;
	} __Request__vm32_mach_make_memory_entry_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t parent_entry;
	} __RequestKData__vm32_mach_make_memory_entry_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		memory_object_size_ut size;
		memory_object_offset_ut offset;
		vm_prot_ut permission;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_mach_make_memory_entry_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t object;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm32_address_ut mask;
		int flags;
		memory_object_offset_ut offset;
		boolean_t copy;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
		vm_inherit_ut inheritance;
	} __Request__vm32_vm_map_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t object;
	} __RequestKData__vm32_vm_map_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		vm32_address_ut mask;
		int flags;
		memory_object_offset_ut offset;
		boolean_t copy;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
		vm_inherit_ut inheritance;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_map_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut address;
		vm_purgable_t control;
		int state;
	} __Request__vm32_vm_purgable_control_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_purgable_control_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm_purgable_t control;
		int state;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_purgable_control_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __Request__vm32_vm_map_exec_lockdown_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_map_exec_lockdown_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_map_exec_lockdown_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		vm32_address_ut src;
		vm32_size_ut src_size;
		vm32_address_ut dst;
		vm32_size_ut dst_size;
		vm32_offset_ut align_mask;
		int options;
		int flags;
	} __Request__vm32_vm_reallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__vm32_vm_reallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut src;
		vm32_size_ut src_size;
		vm32_address_ut dst;
		vm32_size_ut dst_size;
		vm32_offset_ut align_mask;
		int options;
		int flags;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__vm32_vm_reallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
#endif /* !__Request__vm32_map_subsystem__defined */


/* union of all requests */

#ifndef __RequestUnion__vm32_map_subsystem__defined
#define __RequestUnion__vm32_map_subsystem__defined
union __RequestUnion__vm32_map_subsystem {
	__Request__vm32_vm_region_t Request_vm32_vm_region;
	__Request__vm32_vm_allocate_t Request_vm32_vm_allocate;
	__Request__vm32_vm_deallocate_t Request_vm32_vm_deallocate;
	__Request__vm32_vm_protect_t Request_vm32_vm_protect;
	__Request__vm32_vm_inherit_t Request_vm32_vm_inherit;
	__Request__vm32_vm_read_t Request_vm32_vm_read;
	__Request__vm32_vm_read_list_t Request_vm32_vm_read_list;
	__Request__vm32_vm_write_t Request_vm32_vm_write;
	__Request__vm32_vm_copy_t Request_vm32_vm_copy;
	__Request__vm32_vm_read_overwrite_t Request_vm32_vm_read_overwrite;
	__Request__vm32_vm_msync_t Request_vm32_vm_msync;
	__Request__vm32_vm_behavior_set_t Request_vm32_vm_behavior_set;
	__Request__vm32_vm_map_t Request_vm32_vm_map;
	__Request__vm32_vm_machine_attribute_t Request_vm32_vm_machine_attribute;
	__Request__vm32_vm_remap_t Request_vm32_vm_remap;
	__Request__vm32_task_wire_t Request_vm32_task_wire;
	__Request__vm32_mach_make_memory_entry_t Request_vm32_mach_make_memory_entry;
	__Request__vm32_vm_map_page_query_t Request_vm32_vm_map_page_query;
	__Request__vm32_mach_vm_region_info_t Request_vm32_mach_vm_region_info;
	__Request__vm32_vm_mapped_pages_info_t Request_vm32_vm_mapped_pages_info;
	__Request__vm32_vm_region_recurse_t Request_vm32_vm_region_recurse;
	__Request__vm32_vm_region_recurse_64_t Request_vm32_vm_region_recurse_64;
	__Request__vm32_mach_vm_region_info_64_t Request_vm32_mach_vm_region_info_64;
	__Request__vm32_vm_region_64_t Request_vm32_vm_region_64;
	__Request__vm32_mach_make_memory_entry_64_t Request_vm32_mach_make_memory_entry_64;
	__Request__vm32_vm_map_64_t Request_vm32_vm_map_64;
	__Request__vm32_vm_purgable_control_t Request_vm32_vm_purgable_control;
	__Request__vm32_vm_map_exec_lockdown_t Request_vm32_vm_map_exec_lockdown;
	__Request__vm32_vm_reallocate_t Request_vm32_vm_reallocate;
};
#endif /* __RequestUnion__vm32_map_subsystem__defined */
/* typedefs for all replies */

#ifndef __Reply__vm32_map_subsystem__defined
#define __Reply__vm32_map_subsystem__defined

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t object_name;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		mach_msg_type_number_t infoCnt;
		int info[10];
	} __Reply__vm32_vm_region_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t object_name;
	} __ReplyKData__vm32_vm_region_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		mach_msg_type_number_t infoCnt;
		int info[10];
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_region_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut address;
	} __Reply__vm32_vm_allocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_allocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut address;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_allocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
	} __Reply__vm32_vm_deallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_deallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_deallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
	} __Reply__vm32_vm_protect_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_protect_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_protect_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
	} __Reply__vm32_vm_inherit_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_inherit_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_inherit_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_ool_descriptor_t data;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		mach_msg_type_number_t dataCnt;
	} __Reply__vm32_vm_read_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_ool_descriptor_t data;
	} __ReplyKData__vm32_vm_read_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_msg_type_number_t dataCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_read_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_read_entry_t data_list;
	} __Reply__vm32_vm_read_list_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_read_list_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_read_entry_t data_list;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_read_list_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
	} __Reply__vm32_vm_write_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_write_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_write_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
	} __Reply__vm32_vm_copy_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_copy_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_copy_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_size_ut outsize;
	} __Reply__vm32_vm_read_overwrite_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_read_overwrite_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_size_ut outsize;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_read_overwrite_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
	} __Reply__vm32_vm_msync_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_msync_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_msync_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
	} __Reply__vm32_vm_behavior_set_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_behavior_set_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_behavior_set_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut address;
	} __Reply__vm32_vm_map_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_map_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut address;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_map_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm_machine_attribute_val_t value;
	} __Reply__vm32_vm_machine_attribute_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_machine_attribute_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm_machine_attribute_val_t value;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_machine_attribute_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut target_address;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
	} __Reply__vm32_vm_remap_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_remap_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut target_address;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_remap_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
	} __Reply__vm32_task_wire_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_task_wire_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_task_wire_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t object_handle;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		vm32_size_ut size;
	} __Reply__vm32_mach_make_memory_entry_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t object_handle;
	} __ReplyKData__vm32_mach_make_memory_entry_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_size_ut size;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_mach_make_memory_entry_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
		integer_t disposition;
		integer_t ref_count;
	} __Reply__vm32_vm_map_page_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_map_page_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		integer_t disposition;
		integer_t ref_count;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_map_page_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_ool_descriptor_t objects;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		vm_info_region_t region;
		mach_msg_type_number_t objectsCnt;
	} __Reply__vm32_mach_vm_region_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_ool_descriptor_t objects;
	} __ReplyKData__vm32_mach_vm_region_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm_info_region_t region;
		mach_msg_type_number_t objectsCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_mach_vm_region_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_ool_descriptor_t pages;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		mach_msg_type_number_t pagesCnt;
	} __Reply__vm32_vm_mapped_pages_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_ool_descriptor_t pages;
	} __ReplyKData__vm32_vm_mapped_pages_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_msg_type_number_t pagesCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_mapped_pages_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut address;
		vm32_size_ut size;
		natural_t nesting_depth;
		mach_msg_type_number_t infoCnt;
		int info[19];
	} __Reply__vm32_vm_region_recurse_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_region_recurse_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut address;
		vm32_size_ut size;
		natural_t nesting_depth;
		mach_msg_type_number_t infoCnt;
		int info[19];
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_region_recurse_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut address;
		vm32_size_ut size;
		natural_t nesting_depth;
		mach_msg_type_number_t infoCnt;
		int info[19];
	} __Reply__vm32_vm_region_recurse_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_region_recurse_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut address;
		vm32_size_ut size;
		natural_t nesting_depth;
		mach_msg_type_number_t infoCnt;
		int info[19];
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_region_recurse_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_ool_descriptor_t objects;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		vm_info_region_64_t region;
		mach_msg_type_number_t objectsCnt;
	} __Reply__vm32_mach_vm_region_info_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_ool_descriptor_t objects;
	} __ReplyKData__vm32_mach_vm_region_info_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm_info_region_64_t region;
		mach_msg_type_number_t objectsCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_mach_vm_region_info_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t object_name;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		mach_msg_type_number_t infoCnt;
		int info[10];
	} __Reply__vm32_vm_region_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t object_name;
	} __ReplyKData__vm32_vm_region_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		vm32_address_ut address;
		vm32_size_ut size;
		mach_msg_type_number_t infoCnt;
		int info[10];
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_region_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		/* start of the kernel processed data */
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t object_handle;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		memory_object_size_ut size;
	} __Reply__vm32_mach_make_memory_entry_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		mach_msg_body_t msgh_body;
		mach_msg_port_descriptor_t object_handle;
	} __ReplyKData__vm32_mach_make_memory_entry_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		memory_object_size_ut size;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_mach_make_memory_entry_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut address;
	} __Reply__vm32_vm_map_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_map_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut address;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_map_64_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
		int state;
	} __Reply__vm32_vm_purgable_control_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_purgable_control_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		int state;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_purgable_control_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
	} __Reply__vm32_vm_map_exec_lockdown_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_map_exec_lockdown_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_map_exec_lockdown_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut dst;
	} __Reply__vm32_vm_reallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__vm32_vm_reallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		kern_return_t RetCode;
		vm32_address_ut dst;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__vm32_vm_reallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
#endif /* !__Reply__vm32_map_subsystem__defined */


/* union of all replies */

#ifndef __ReplyUnion__vm32_map_subsystem__defined
#define __ReplyUnion__vm32_map_subsystem__defined
union __ReplyUnion__vm32_map_subsystem {
	__Reply__vm32_vm_region_t Reply_vm32_vm_region;
	__Reply__vm32_vm_allocate_t Reply_vm32_vm_allocate;
	__Reply__vm32_vm_deallocate_t Reply_vm32_vm_deallocate;
	__Reply__vm32_vm_protect_t Reply_vm32_vm_protect;
	__Reply__vm32_vm_inherit_t Reply_vm32_vm_inherit;
	__Reply__vm32_vm_read_t Reply_vm32_vm_read;
	__Reply__vm32_vm_read_list_t Reply_vm32_vm_read_list;
	__Reply__vm32_vm_write_t Reply_vm32_vm_write;
	__Reply__vm32_vm_copy_t Reply_vm32_vm_copy;
	__Reply__vm32_vm_read_overwrite_t Reply_vm32_vm_read_overwrite;
	__Reply__vm32_vm_msync_t Reply_vm32_vm_msync;
	__Reply__vm32_vm_behavior_set_t Reply_vm32_vm_behavior_set;
	__Reply__vm32_vm_map_t Reply_vm32_vm_map;
	__Reply__vm32_vm_machine_attribute_t Reply_vm32_vm_machine_attribute;
	__Reply__vm32_vm_remap_t Reply_vm32_vm_remap;
	__Reply__vm32_task_wire_t Reply_vm32_task_wire;
	__Reply__vm32_mach_make_memory_entry_t Reply_vm32_mach_make_memory_entry;
	__Reply__vm32_vm_map_page_query_t Reply_vm32_vm_map_page_query;
	__Reply__vm32_mach_vm_region_info_t Reply_vm32_mach_vm_region_info;
	__Reply__vm32_vm_mapped_pages_info_t Reply_vm32_vm_mapped_pages_info;
	__Reply__vm32_vm_region_recurse_t Reply_vm32_vm_region_recurse;
	__Reply__vm32_vm_region_recurse_64_t Reply_vm32_vm_region_recurse_64;
	__Reply__vm32_mach_vm_region_info_64_t Reply_vm32_mach_vm_region_info_64;
	__Reply__vm32_vm_region_64_t Reply_vm32_vm_region_64;
	__Reply__vm32_mach_make_memory_entry_64_t Reply_vm32_mach_make_memory_entry_64;
	__Reply__vm32_vm_map_64_t Reply_vm32_vm_map_64;
	__Reply__vm32_vm_purgable_control_t Reply_vm32_vm_purgable_control;
	__Reply__vm32_vm_map_exec_lockdown_t Reply_vm32_vm_map_exec_lockdown;
	__Reply__vm32_vm_reallocate_t Reply_vm32_vm_reallocate;
};
#endif /* __ReplyUnion__vm32_map_subsystem__defined */

#ifndef subsystem_to_name_map_vm32_map
#define subsystem_to_name_map_vm32_map \
    { "vm32_vm_region", 3800 },\
    { "vm32_vm_allocate", 3801 },\
    { "vm32_vm_deallocate", 3802 },\
    { "vm32_vm_protect", 3803 },\
    { "vm32_vm_inherit", 3804 },\
    { "vm32_vm_read", 3805 },\
    { "vm32_vm_read_list", 3806 },\
    { "vm32_vm_write", 3807 },\
    { "vm32_vm_copy", 3808 },\
    { "vm32_vm_read_overwrite", 3809 },\
    { "vm32_vm_msync", 3810 },\
    { "vm32_vm_behavior_set", 3811 },\
    { "vm32_vm_map", 3812 },\
    { "vm32_vm_machine_attribute", 3813 },\
    { "vm32_vm_remap", 3814 },\
    { "vm32_task_wire", 3815 },\
    { "vm32_mach_make_memory_entry", 3816 },\
    { "vm32_vm_map_page_query", 3817 },\
    { "vm32_mach_vm_region_info", 3818 },\
    { "vm32_vm_mapped_pages_info", 3819 },\
    { "vm32_vm_region_recurse", 3821 },\
    { "vm32_vm_region_recurse_64", 3822 },\
    { "vm32_mach_vm_region_info_64", 3823 },\
    { "vm32_vm_region_64", 3824 },\
    { "vm32_mach_make_memory_entry_64", 3825 },\
    { "vm32_vm_map_64", 3826 },\
    { "vm32_vm_purgable_control", 3830 },\
    { "vm32_vm_map_exec_lockdown", 3831 },\
    { "vm32_vm_reallocate", 3833 }
#endif

#ifdef __AfterMigServerHeader
__AfterMigServerHeader
#endif /* __AfterMigServerHeader */

#endif	 /* _vm32_map_server_ */
