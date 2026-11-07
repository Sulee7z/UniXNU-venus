#ifndef	_mach_vm_server_
#define	_mach_vm_server_

/* Module mach_vm */

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

#ifndef	mach_vm_MSG_COUNT
#define	mach_vm_MSG_COUNT	30
#endif	/* mach_vm_MSG_COUNT */

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


/* Routine mach_vm_allocate_external */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_allocate_external
(
	vm_map_t target,
	mach_vm_address_ut *address,
	mach_vm_size_ut size,
	int flags
);

/* Routine mach_vm_deallocate_external */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_deallocate_external
(
	vm_map_t target,
	mach_vm_address_ut address,
	mach_vm_size_ut size
);

/* Routine mach_vm_protect */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_protect
(
	vm_map_t target_task,
	mach_vm_address_ut address,
	mach_vm_size_ut size,
	boolean_t set_maximum,
	vm_prot_ut new_protection
);

/* Routine mach_vm_inherit */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_inherit
(
	vm_map_t target_task,
	mach_vm_address_ut address,
	mach_vm_size_ut size,
	vm_inherit_ut new_inheritance
);

/* Routine mach_vm_read */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_read
(
	vm_map_read_t target_task,
	mach_vm_address_ut address,
	mach_vm_size_ut size,
	pointer_ut *data,
	mach_msg_type_number_t *dataCnt
);

/* Routine mach_vm_read_list */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_read_list
(
	vm_map_read_t target_task,
	mach_vm_read_entry_t data_list,
	natural_t count
);

/* Routine mach_vm_write */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_write
(
	vm_map_t target_task,
	mach_vm_address_ut address,
	pointer_ut data,
	mach_msg_type_number_t dataCnt
);

/* Routine mach_vm_copy */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_copy
(
	vm_map_t target_task,
	mach_vm_address_ut source_address,
	mach_vm_size_ut size,
	mach_vm_address_ut dest_address
);

/* Routine mach_vm_read_overwrite */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_read_overwrite
(
	vm_map_read_t target_task,
	mach_vm_address_ut address,
	mach_vm_size_ut size,
	mach_vm_address_ut data,
	mach_vm_size_ut *outsize
);

/* Routine mach_vm_msync */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_msync
(
	vm_map_t target_task,
	mach_vm_address_ut address,
	mach_vm_size_ut size,
	vm_sync_t sync_flags
);

/* Routine mach_vm_behavior_set */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_behavior_set
(
	vm_map_t target_task,
	mach_vm_address_ut address,
	mach_vm_size_ut size,
	vm_behavior_ut new_behavior
);

/* Routine mach_vm_map_external */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_map_external
(
	vm_map_t target_task,
	mach_vm_address_ut *address,
	mach_vm_size_ut size,
	mach_vm_offset_ut mask,
	int flags,
	mem_entry_name_port_t object,
	memory_object_offset_ut offset,
	boolean_t copy,
	vm_prot_ut cur_protection,
	vm_prot_ut max_protection,
	vm_inherit_ut inheritance
);

/* Routine mach_vm_machine_attribute */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_machine_attribute
(
	vm_map_t target_task,
	mach_vm_address_ut address,
	mach_vm_size_ut size,
	vm_machine_attribute_t attribute,
	vm_machine_attribute_val_t *value
);

/* Routine mach_vm_remap_external */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_remap_external
(
	vm_map_t target_task,
	mach_vm_address_ut *target_address,
	mach_vm_size_ut size,
	mach_vm_offset_ut mask,
	int flags,
	vm_map_t src_task,
	mach_vm_address_ut src_address,
	boolean_t copy,
	vm_prot_ut *cur_protection,
	vm_prot_ut *max_protection,
	vm_inherit_ut inheritance
);

/* Routine mach_vm_page_query */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_page_query
(
	vm_map_read_t target_map,
	mach_vm_offset_ut offset,
	integer_t *disposition,
	integer_t *ref_count
);

/* Routine mach_vm_region_recurse */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_region_recurse
(
	vm_map_read_t target_task,
	mach_vm_address_ut *address,
	mach_vm_size_ut *size,
	natural_t *nesting_depth,
	vm_region_recurse_info_t info,
	mach_msg_type_number_t *infoCnt
);

/* Routine mach_vm_region */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_region
(
	vm_map_read_t target_task,
	mach_vm_address_ut *address,
	mach_vm_size_ut *size,
	vm_region_flavor_t flavor,
	vm_region_info_t info,
	mach_msg_type_number_t *infoCnt,
	mach_port_t *object_name
);

/* Routine _mach_make_memory_entry */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t _mach_make_memory_entry
(
	vm_map_t target_task,
	memory_object_size_ut *size,
	memory_object_offset_ut offset,
	vm_prot_ut permission,
	mem_entry_name_port_t *object_handle,
	mem_entry_name_port_t parent_handle
);

/* Routine mach_vm_purgable_control_external */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_purgable_control_external
(
	mach_port_t target_tport,
	mach_vm_address_ut address,
	vm_purgable_t control,
	int *state
);

/* Routine mach_vm_page_info */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_page_info
(
	vm_map_read_t target_task,
	mach_vm_address_ut address,
	vm_page_info_flavor_t flavor,
	vm_page_info_t info,
	mach_msg_type_number_t *infoCnt
);

/* Routine mach_vm_page_range_query */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_page_range_query
(
	vm_map_read_t target_map,
	mach_vm_offset_ut address,
	mach_vm_size_ut size,
	mach_vm_address_ut dispositions,
	mach_vm_size_ut *dispositions_count
);

/* Routine mach_vm_remap_new_external */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_remap_new_external
(
	vm_map_t target_task,
	mach_vm_address_ut *target_address,
	mach_vm_size_ut size,
	mach_vm_offset_ut mask,
	int flags,
	mach_port_t src_tport,
	mach_vm_address_ut src_address,
	boolean_t copy,
	vm_prot_ut *cur_protection,
	vm_prot_ut *max_protection,
	vm_inherit_ut inheritance
);

/* Routine mach_vm_deferred_reclamation_buffer_allocate */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_deferred_reclamation_buffer_allocate
(
	task_t target_task,
	mach_vm_address_ut *address,
	uint64_t *next_deadline,
	uint32_t len,
	uint32_t max_len
);

/* Routine mach_vm_deferred_reclamation_buffer_flush */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_deferred_reclamation_buffer_flush
(
	task_t target_task,
	uint32_t num_entries_to_reclaim,
	uint64_t *bytes_reclaimed,
	uint64_t *next_deadline
);

/* Routine mach_vm_range_create */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_range_create
(
	vm_map_t target_task,
	mach_vm_range_flavor_t flavor,
	mach_vm_range_recipes_raw_t recipes,
	mach_msg_type_number_t recipesCnt
);

/* Routine mach_vm_deferred_reclamation_buffer_resize */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_deferred_reclamation_buffer_resize
(
	task_t target_task,
	uint32_t new_len,
	uint64_t *bytes_reclaimed,
	uint64_t *next_deadline
);

/* Routine mach_vm_update_pointers_with_remote_tags */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_update_pointers_with_remote_tags
(
	vm_map_t target,
	mach_vm_offset_list_t in_pointer_list,
	mach_msg_type_number_t in_pointer_listCnt,
	mach_vm_offset_list_t out_pointer_list,
	mach_msg_type_number_t *out_pointer_listCnt
);

/* Routine mach_vm_deferred_reclamation_buffer_query */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_deferred_reclamation_buffer_query
(
	task_read_t target,
	mach_vm_address_ut *addr,
	mach_vm_size_ut *size
);

/* Routine mach_vm_reallocate */
#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
MIG_SERVER_ROUTINE
kern_return_t mach_vm_reallocate
(
	vm_map_t target_task,
	mach_vm_address_ut src,
	mach_vm_size_ut src_size,
	mach_vm_address_ut *dst,
	mach_vm_size_ut dst_size,
	mach_vm_offset_ut align_mask,
	int options,
	int flags
);

#ifdef	mig_external
mig_external
#else
extern
#endif	/* mig_external */
boolean_t mach_vm_server(
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
mig_kern_routine_t mach_vm_server_routine(
		mach_msg_header_t *InHeadP);


/* Description of this kernel subsystem, for use in direct RPC */
extern const struct mach_vm_subsystem {
	mig_kern_server_routine_t	kserver;	/* Server routine */
	mach_msg_id_t	start;	/* Min routine number */
	mach_msg_id_t	end;	/* Max routine number + 1 */
	unsigned int	maxsize;	/* Max msg size */
	vm_address_t	reserved;	/* Reserved */
	struct kern_routine_descriptor	/* Array of routine descriptors */
		kroutine[30];
} mach_vm_subsystem;

/* typedefs for all requests */

#ifndef __Request__mach_vm_subsystem__defined
#define __Request__mach_vm_subsystem__defined

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		int flags;
	} __Request__mach_vm_allocate_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_allocate_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		int flags;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_allocate_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
	} __Request__mach_vm_deallocate_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_deallocate_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_deallocate_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		boolean_t set_maximum;
		vm_prot_ut new_protection;
	} __Request__mach_vm_protect_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_protect_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		boolean_t set_maximum;
		vm_prot_ut new_protection;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_protect_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		vm_inherit_ut new_inheritance;
	} __Request__mach_vm_inherit_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_inherit_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		vm_inherit_ut new_inheritance;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_inherit_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
	} __Request__mach_vm_read_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_read_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_read_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_read_entry_t data_list;
		natural_t count;
	} __Request__mach_vm_read_list_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_read_list_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_read_entry_t data_list;
		natural_t count;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_read_list_t __attribute__((unused));
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
		mach_vm_address_ut address;
		mach_msg_type_number_t dataCnt;
	} __Request__mach_vm_write_t __attribute__((unused));
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
	} __RequestKData__mach_vm_write_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_msg_type_number_t dataCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_write_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut source_address;
		mach_vm_size_ut size;
		mach_vm_address_ut dest_address;
	} __Request__mach_vm_copy_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_copy_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut source_address;
		mach_vm_size_ut size;
		mach_vm_address_ut dest_address;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_copy_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		mach_vm_address_ut data;
	} __Request__mach_vm_read_overwrite_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_read_overwrite_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		mach_vm_address_ut data;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_read_overwrite_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		vm_sync_t sync_flags;
	} __Request__mach_vm_msync_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_msync_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		vm_sync_t sync_flags;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_msync_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		vm_behavior_ut new_behavior;
	} __Request__mach_vm_behavior_set_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_behavior_set_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		vm_behavior_ut new_behavior;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_behavior_set_t __attribute__((unused));
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
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		mach_vm_offset_ut mask;
		int flags;
		memory_object_offset_ut offset;
		boolean_t copy;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
		vm_inherit_ut inheritance;
	} __Request__mach_vm_map_external_t __attribute__((unused));
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
	} __RequestKData__mach_vm_map_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		mach_vm_offset_ut mask;
		int flags;
		memory_object_offset_ut offset;
		boolean_t copy;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
		vm_inherit_ut inheritance;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_map_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		vm_machine_attribute_t attribute;
		vm_machine_attribute_val_t value;
	} __Request__mach_vm_machine_attribute_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_machine_attribute_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		vm_machine_attribute_t attribute;
		vm_machine_attribute_val_t value;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_machine_attribute_t __attribute__((unused));
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
		mach_vm_address_ut target_address;
		mach_vm_size_ut size;
		mach_vm_offset_ut mask;
		int flags;
		mach_vm_address_ut src_address;
		boolean_t copy;
		vm_inherit_ut inheritance;
	} __Request__mach_vm_remap_external_t __attribute__((unused));
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
	} __RequestKData__mach_vm_remap_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut target_address;
		mach_vm_size_ut size;
		mach_vm_offset_ut mask;
		int flags;
		mach_vm_address_ut src_address;
		boolean_t copy;
		vm_inherit_ut inheritance;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_remap_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_offset_ut offset;
	} __Request__mach_vm_page_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_page_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_offset_ut offset;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_page_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut address;
		natural_t nesting_depth;
		mach_msg_type_number_t infoCnt;
	} __Request__mach_vm_region_recurse_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_region_recurse_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		natural_t nesting_depth;
		mach_msg_type_number_t infoCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_region_recurse_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut address;
		vm_region_flavor_t flavor;
		mach_msg_type_number_t infoCnt;
	} __Request__mach_vm_region_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_region_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		vm_region_flavor_t flavor;
		mach_msg_type_number_t infoCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_region_t __attribute__((unused));
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
		mach_msg_port_descriptor_t parent_handle;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		memory_object_size_ut size;
		memory_object_offset_ut offset;
		vm_prot_ut permission;
	} __Request___mach_make_memory_entry_t __attribute__((unused));
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
		mach_msg_port_descriptor_t parent_handle;
	} __RequestKData___mach_make_memory_entry_t __attribute__((unused));
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
	} __RequestUData___mach_make_memory_entry_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut address;
		vm_purgable_t control;
		int state;
	} __Request__mach_vm_purgable_control_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_purgable_control_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		vm_purgable_t control;
		int state;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_purgable_control_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut address;
		vm_page_info_flavor_t flavor;
		mach_msg_type_number_t infoCnt;
	} __Request__mach_vm_page_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_page_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		vm_page_info_flavor_t flavor;
		mach_msg_type_number_t infoCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_page_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_offset_ut address;
		mach_vm_size_ut size;
		mach_vm_address_ut dispositions;
		mach_vm_size_ut dispositions_count;
	} __Request__mach_vm_page_range_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_page_range_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_offset_ut address;
		mach_vm_size_ut size;
		mach_vm_address_ut dispositions;
		mach_vm_size_ut dispositions_count;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_page_range_query_t __attribute__((unused));
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
		mach_msg_port_descriptor_t src_tport;
		/* end of the kernel processed data */
		NDR_record_t NDR;
		mach_vm_address_ut target_address;
		mach_vm_size_ut size;
		mach_vm_offset_ut mask;
		int flags;
		mach_vm_address_ut src_address;
		boolean_t copy;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
		vm_inherit_ut inheritance;
	} __Request__mach_vm_remap_new_external_t __attribute__((unused));
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
		mach_msg_port_descriptor_t src_tport;
	} __RequestKData__mach_vm_remap_new_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut target_address;
		mach_vm_size_ut size;
		mach_vm_offset_ut mask;
		int flags;
		mach_vm_address_ut src_address;
		boolean_t copy;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
		vm_inherit_ut inheritance;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_remap_new_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		uint32_t len;
		uint32_t max_len;
	} __Request__mach_vm_deferred_reclamation_buffer_allocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_deferred_reclamation_buffer_allocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		uint32_t len;
		uint32_t max_len;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_deferred_reclamation_buffer_allocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		uint32_t num_entries_to_reclaim;
	} __Request__mach_vm_deferred_reclamation_buffer_flush_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_deferred_reclamation_buffer_flush_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		uint32_t num_entries_to_reclaim;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_deferred_reclamation_buffer_flush_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_range_flavor_t flavor;
		mach_msg_type_number_t recipesCnt;
		uint8_t recipes[1024];
	} __Request__mach_vm_range_create_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_range_create_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_range_flavor_t flavor;
		mach_msg_type_number_t recipesCnt;
		uint8_t recipes[1024];
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_range_create_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		uint32_t new_len;
	} __Request__mach_vm_deferred_reclamation_buffer_resize_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_deferred_reclamation_buffer_resize_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		uint32_t new_len;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_deferred_reclamation_buffer_resize_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_msg_type_number_t in_pointer_listCnt;
		mach_vm_offset_ut in_pointer_list[1024];
		mach_msg_type_number_t out_pointer_listCnt;
	} __Request__mach_vm_update_pointers_with_remote_tags_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_update_pointers_with_remote_tags_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_msg_type_number_t in_pointer_listCnt;
		mach_vm_offset_ut in_pointer_list[1024];
		mach_msg_type_number_t out_pointer_listCnt;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_update_pointers_with_remote_tags_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __Request__mach_vm_deferred_reclamation_buffer_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_deferred_reclamation_buffer_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_deferred_reclamation_buffer_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		mach_vm_address_ut src;
		mach_vm_size_ut src_size;
		mach_vm_address_ut dst;
		mach_vm_size_ut dst_size;
		mach_vm_offset_ut align_mask;
		int options;
		int flags;
	} __Request__mach_vm_reallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __RequestKData__mach_vm_reallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut src;
		mach_vm_size_ut src_size;
		mach_vm_address_ut dst;
		mach_vm_size_ut dst_size;
		mach_vm_offset_ut align_mask;
		int options;
		int flags;
		char padding[0]; /* Avoid generating empty UData structs */
	} __RequestUData__mach_vm_reallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
#endif /* !__Request__mach_vm_subsystem__defined */


/* union of all requests */

#ifndef __RequestUnion__mach_vm_subsystem__defined
#define __RequestUnion__mach_vm_subsystem__defined
union __RequestUnion__mach_vm_subsystem {
	__Request__mach_vm_allocate_external_t Request_mach_vm_allocate_external;
	__Request__mach_vm_deallocate_external_t Request_mach_vm_deallocate_external;
	__Request__mach_vm_protect_t Request_mach_vm_protect;
	__Request__mach_vm_inherit_t Request_mach_vm_inherit;
	__Request__mach_vm_read_t Request_mach_vm_read;
	__Request__mach_vm_read_list_t Request_mach_vm_read_list;
	__Request__mach_vm_write_t Request_mach_vm_write;
	__Request__mach_vm_copy_t Request_mach_vm_copy;
	__Request__mach_vm_read_overwrite_t Request_mach_vm_read_overwrite;
	__Request__mach_vm_msync_t Request_mach_vm_msync;
	__Request__mach_vm_behavior_set_t Request_mach_vm_behavior_set;
	__Request__mach_vm_map_external_t Request_mach_vm_map_external;
	__Request__mach_vm_machine_attribute_t Request_mach_vm_machine_attribute;
	__Request__mach_vm_remap_external_t Request_mach_vm_remap_external;
	__Request__mach_vm_page_query_t Request_mach_vm_page_query;
	__Request__mach_vm_region_recurse_t Request_mach_vm_region_recurse;
	__Request__mach_vm_region_t Request_mach_vm_region;
	__Request___mach_make_memory_entry_t Request__mach_make_memory_entry;
	__Request__mach_vm_purgable_control_external_t Request_mach_vm_purgable_control_external;
	__Request__mach_vm_page_info_t Request_mach_vm_page_info;
	__Request__mach_vm_page_range_query_t Request_mach_vm_page_range_query;
	__Request__mach_vm_remap_new_external_t Request_mach_vm_remap_new_external;
	__Request__mach_vm_deferred_reclamation_buffer_allocate_t Request_mach_vm_deferred_reclamation_buffer_allocate;
	__Request__mach_vm_deferred_reclamation_buffer_flush_t Request_mach_vm_deferred_reclamation_buffer_flush;
	__Request__mach_vm_range_create_t Request_mach_vm_range_create;
	__Request__mach_vm_deferred_reclamation_buffer_resize_t Request_mach_vm_deferred_reclamation_buffer_resize;
	__Request__mach_vm_update_pointers_with_remote_tags_t Request_mach_vm_update_pointers_with_remote_tags;
	__Request__mach_vm_deferred_reclamation_buffer_query_t Request_mach_vm_deferred_reclamation_buffer_query;
	__Request__mach_vm_reallocate_t Request_mach_vm_reallocate;
};
#endif /* __RequestUnion__mach_vm_subsystem__defined */
/* typedefs for all replies */

#ifndef __Reply__mach_vm_subsystem__defined
#define __Reply__mach_vm_subsystem__defined

#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
		NDR_record_t NDR;
		kern_return_t RetCode;
		mach_vm_address_ut address;
	} __Reply__mach_vm_allocate_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_allocate_external_t __attribute__((unused));
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
		mach_vm_address_ut address;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_allocate_external_t __attribute__((unused));
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
	} __Reply__mach_vm_deallocate_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_deallocate_external_t __attribute__((unused));
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
	} __ReplyUData__mach_vm_deallocate_external_t __attribute__((unused));
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
	} __Reply__mach_vm_protect_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_protect_t __attribute__((unused));
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
	} __ReplyUData__mach_vm_protect_t __attribute__((unused));
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
	} __Reply__mach_vm_inherit_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_inherit_t __attribute__((unused));
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
	} __ReplyUData__mach_vm_inherit_t __attribute__((unused));
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
	} __Reply__mach_vm_read_t __attribute__((unused));
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
	} __ReplyKData__mach_vm_read_t __attribute__((unused));
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
	} __ReplyUData__mach_vm_read_t __attribute__((unused));
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
		mach_vm_read_entry_t data_list;
	} __Reply__mach_vm_read_list_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_read_list_t __attribute__((unused));
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
		mach_vm_read_entry_t data_list;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_read_list_t __attribute__((unused));
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
	} __Reply__mach_vm_write_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_write_t __attribute__((unused));
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
	} __ReplyUData__mach_vm_write_t __attribute__((unused));
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
	} __Reply__mach_vm_copy_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_copy_t __attribute__((unused));
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
	} __ReplyUData__mach_vm_copy_t __attribute__((unused));
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
		mach_vm_size_ut outsize;
	} __Reply__mach_vm_read_overwrite_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_read_overwrite_t __attribute__((unused));
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
		mach_vm_size_ut outsize;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_read_overwrite_t __attribute__((unused));
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
	} __Reply__mach_vm_msync_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_msync_t __attribute__((unused));
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
	} __ReplyUData__mach_vm_msync_t __attribute__((unused));
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
	} __Reply__mach_vm_behavior_set_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_behavior_set_t __attribute__((unused));
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
	} __ReplyUData__mach_vm_behavior_set_t __attribute__((unused));
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
		mach_vm_address_ut address;
	} __Reply__mach_vm_map_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_map_external_t __attribute__((unused));
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
		mach_vm_address_ut address;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_map_external_t __attribute__((unused));
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
	} __Reply__mach_vm_machine_attribute_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_machine_attribute_t __attribute__((unused));
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
	} __ReplyUData__mach_vm_machine_attribute_t __attribute__((unused));
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
		mach_vm_address_ut target_address;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
	} __Reply__mach_vm_remap_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_remap_external_t __attribute__((unused));
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
		mach_vm_address_ut target_address;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_remap_external_t __attribute__((unused));
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
	} __Reply__mach_vm_page_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_page_query_t __attribute__((unused));
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
	} __ReplyUData__mach_vm_page_query_t __attribute__((unused));
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
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		natural_t nesting_depth;
		mach_msg_type_number_t infoCnt;
		int info[19];
	} __Reply__mach_vm_region_recurse_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_region_recurse_t __attribute__((unused));
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
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		natural_t nesting_depth;
		mach_msg_type_number_t infoCnt;
		int info[19];
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_region_recurse_t __attribute__((unused));
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
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		mach_msg_type_number_t infoCnt;
		int info[10];
	} __Reply__mach_vm_region_t __attribute__((unused));
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
	} __ReplyKData__mach_vm_region_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for pure user data */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		NDR_record_t NDR;
		mach_vm_address_ut address;
		mach_vm_size_ut size;
		mach_msg_type_number_t infoCnt;
		int info[10];
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_region_t __attribute__((unused));
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
	} __Reply___mach_make_memory_entry_t __attribute__((unused));
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
	} __ReplyKData___mach_make_memory_entry_t __attribute__((unused));
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
	} __ReplyUData___mach_make_memory_entry_t __attribute__((unused));
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
	} __Reply__mach_vm_purgable_control_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_purgable_control_external_t __attribute__((unused));
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
	} __ReplyUData__mach_vm_purgable_control_external_t __attribute__((unused));
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
		mach_msg_type_number_t infoCnt;
		int info[32];
	} __Reply__mach_vm_page_info_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_page_info_t __attribute__((unused));
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
		mach_msg_type_number_t infoCnt;
		int info[32];
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_page_info_t __attribute__((unused));
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
		mach_vm_size_ut dispositions_count;
	} __Reply__mach_vm_page_range_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_page_range_query_t __attribute__((unused));
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
		mach_vm_size_ut dispositions_count;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_page_range_query_t __attribute__((unused));
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
		mach_vm_address_ut target_address;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
	} __Reply__mach_vm_remap_new_external_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_remap_new_external_t __attribute__((unused));
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
		mach_vm_address_ut target_address;
		vm_prot_ut cur_protection;
		vm_prot_ut max_protection;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_remap_new_external_t __attribute__((unused));
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
		mach_vm_address_ut address;
		uint64_t next_deadline;
	} __Reply__mach_vm_deferred_reclamation_buffer_allocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_deferred_reclamation_buffer_allocate_t __attribute__((unused));
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
		mach_vm_address_ut address;
		uint64_t next_deadline;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_deferred_reclamation_buffer_allocate_t __attribute__((unused));
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
		uint64_t bytes_reclaimed;
		uint64_t next_deadline;
	} __Reply__mach_vm_deferred_reclamation_buffer_flush_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_deferred_reclamation_buffer_flush_t __attribute__((unused));
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
		uint64_t bytes_reclaimed;
		uint64_t next_deadline;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_deferred_reclamation_buffer_flush_t __attribute__((unused));
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
	} __Reply__mach_vm_range_create_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_range_create_t __attribute__((unused));
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
	} __ReplyUData__mach_vm_range_create_t __attribute__((unused));
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
		uint64_t bytes_reclaimed;
		uint64_t next_deadline;
	} __Reply__mach_vm_deferred_reclamation_buffer_resize_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_deferred_reclamation_buffer_resize_t __attribute__((unused));
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
		uint64_t bytes_reclaimed;
		uint64_t next_deadline;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_deferred_reclamation_buffer_resize_t __attribute__((unused));
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
		mach_msg_type_number_t out_pointer_listCnt;
		mach_vm_offset_ut out_pointer_list[1024];
	} __Reply__mach_vm_update_pointers_with_remote_tags_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_update_pointers_with_remote_tags_t __attribute__((unused));
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
		mach_msg_type_number_t out_pointer_listCnt;
		mach_vm_offset_ut out_pointer_list[1024];
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_update_pointers_with_remote_tags_t __attribute__((unused));
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
		mach_vm_address_ut addr;
		mach_vm_size_ut size;
	} __Reply__mach_vm_deferred_reclamation_buffer_query_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_deferred_reclamation_buffer_query_t __attribute__((unused));
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
		mach_vm_address_ut addr;
		mach_vm_size_ut size;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_deferred_reclamation_buffer_query_t __attribute__((unused));
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
		mach_vm_address_ut dst;
	} __Reply__mach_vm_reallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
/* Struct for kernel processed data (Header + Descriptors) */
#ifdef  __MigPackStructs
#pragma pack(push, 4)
#endif
	typedef struct {
		mach_msg_header_t Head;
	} __ReplyKData__mach_vm_reallocate_t __attribute__((unused));
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
		mach_vm_address_ut dst;
		char padding[0]; /* Avoid generating empty UData structs */
	} __ReplyUData__mach_vm_reallocate_t __attribute__((unused));
#ifdef  __MigPackStructs
#pragma pack(pop)
#endif
#endif /* !__Reply__mach_vm_subsystem__defined */


/* union of all replies */

#ifndef __ReplyUnion__mach_vm_subsystem__defined
#define __ReplyUnion__mach_vm_subsystem__defined
union __ReplyUnion__mach_vm_subsystem {
	__Reply__mach_vm_allocate_external_t Reply_mach_vm_allocate_external;
	__Reply__mach_vm_deallocate_external_t Reply_mach_vm_deallocate_external;
	__Reply__mach_vm_protect_t Reply_mach_vm_protect;
	__Reply__mach_vm_inherit_t Reply_mach_vm_inherit;
	__Reply__mach_vm_read_t Reply_mach_vm_read;
	__Reply__mach_vm_read_list_t Reply_mach_vm_read_list;
	__Reply__mach_vm_write_t Reply_mach_vm_write;
	__Reply__mach_vm_copy_t Reply_mach_vm_copy;
	__Reply__mach_vm_read_overwrite_t Reply_mach_vm_read_overwrite;
	__Reply__mach_vm_msync_t Reply_mach_vm_msync;
	__Reply__mach_vm_behavior_set_t Reply_mach_vm_behavior_set;
	__Reply__mach_vm_map_external_t Reply_mach_vm_map_external;
	__Reply__mach_vm_machine_attribute_t Reply_mach_vm_machine_attribute;
	__Reply__mach_vm_remap_external_t Reply_mach_vm_remap_external;
	__Reply__mach_vm_page_query_t Reply_mach_vm_page_query;
	__Reply__mach_vm_region_recurse_t Reply_mach_vm_region_recurse;
	__Reply__mach_vm_region_t Reply_mach_vm_region;
	__Reply___mach_make_memory_entry_t Reply__mach_make_memory_entry;
	__Reply__mach_vm_purgable_control_external_t Reply_mach_vm_purgable_control_external;
	__Reply__mach_vm_page_info_t Reply_mach_vm_page_info;
	__Reply__mach_vm_page_range_query_t Reply_mach_vm_page_range_query;
	__Reply__mach_vm_remap_new_external_t Reply_mach_vm_remap_new_external;
	__Reply__mach_vm_deferred_reclamation_buffer_allocate_t Reply_mach_vm_deferred_reclamation_buffer_allocate;
	__Reply__mach_vm_deferred_reclamation_buffer_flush_t Reply_mach_vm_deferred_reclamation_buffer_flush;
	__Reply__mach_vm_range_create_t Reply_mach_vm_range_create;
	__Reply__mach_vm_deferred_reclamation_buffer_resize_t Reply_mach_vm_deferred_reclamation_buffer_resize;
	__Reply__mach_vm_update_pointers_with_remote_tags_t Reply_mach_vm_update_pointers_with_remote_tags;
	__Reply__mach_vm_deferred_reclamation_buffer_query_t Reply_mach_vm_deferred_reclamation_buffer_query;
	__Reply__mach_vm_reallocate_t Reply_mach_vm_reallocate;
};
#endif /* __ReplyUnion__mach_vm_subsystem__defined */

#ifndef subsystem_to_name_map_mach_vm
#define subsystem_to_name_map_mach_vm \
    { "mach_vm_allocate_external", 4800 },\
    { "mach_vm_deallocate_external", 4801 },\
    { "mach_vm_protect", 4802 },\
    { "mach_vm_inherit", 4803 },\
    { "mach_vm_read", 4804 },\
    { "mach_vm_read_list", 4805 },\
    { "mach_vm_write", 4806 },\
    { "mach_vm_copy", 4807 },\
    { "mach_vm_read_overwrite", 4808 },\
    { "mach_vm_msync", 4809 },\
    { "mach_vm_behavior_set", 4810 },\
    { "mach_vm_map_external", 4811 },\
    { "mach_vm_machine_attribute", 4812 },\
    { "mach_vm_remap_external", 4813 },\
    { "mach_vm_page_query", 4814 },\
    { "mach_vm_region_recurse", 4815 },\
    { "mach_vm_region", 4816 },\
    { "_mach_make_memory_entry", 4817 },\
    { "mach_vm_purgable_control_external", 4818 },\
    { "mach_vm_page_info", 4819 },\
    { "mach_vm_page_range_query", 4820 },\
    { "mach_vm_remap_new_external", 4821 },\
    { "mach_vm_deferred_reclamation_buffer_allocate", 4822 },\
    { "mach_vm_deferred_reclamation_buffer_flush", 4823 },\
    { "mach_vm_range_create", 4825 },\
    { "mach_vm_deferred_reclamation_buffer_resize", 4826 },\
    { "mach_vm_update_pointers_with_remote_tags", 4827 },\
    { "mach_vm_deferred_reclamation_buffer_query", 4828 },\
    { "mach_vm_reallocate", 4829 }
#endif

#ifdef __AfterMigServerHeader
__AfterMigServerHeader
#endif /* __AfterMigServerHeader */

#endif	 /* _mach_vm_server_ */
