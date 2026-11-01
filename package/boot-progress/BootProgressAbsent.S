/*
 * Drivers this board does not build. BootProgress.c checks each data address
 * before use; absolute zero keeps those optional rows off. The few functions
 * are referenced through weak pointers and never reached when their data
 * counterparts are zero, but a callable stub keeps the static link bounded.
 */
.globl _boot_process_attempts
.set _boot_process_attempts, 0
.globl _boot_process_busy
.set _boot_process_busy, 0
.globl _boot_process_passes
.set _boot_process_passes, 0
.globl _boot_process_rows
.set _boot_process_rows, 0
.globl _boot_process_seen
.set _boot_process_seen, 0
.globl _boot_ui_trace_index
.set _boot_ui_trace_index, 0
.globl _boot_ui_trace_label
.set _boot_ui_trace_label, 0
.globl _boot_ui_trace_phase
.set _boot_ui_trace_phase, 0
.globl _boot_ui_trace_ready
.set _boot_ui_trace_ready, 0
.globl _boot_ui_trace_rows
.set _boot_ui_trace_rows, 0
.globl _native_cpufreq_row
.set _native_cpufreq_row, 0
.globl _native_cpufreq_stage
.set _native_cpufreq_stage, 0
.globl _native_touch_rows
.set _native_touch_rows, 0
.globl _native_touch_stage_req
.set _native_touch_stage_req, 0

.globl _native_adreno_audit_attr
.set _native_adreno_audit_attr, 0
.globl _native_adreno_audit_ticks
.set _native_adreno_audit_ticks, 0
.text
.p2align 2
.globl _boot_diag_scan
.weak_definition _boot_diag_scan
_boot_diag_scan:
	mov	w0, #0
	ret
.globl _boot_diag_stream
.weak_definition _boot_diag_stream
_boot_diag_stream:
	mov	w0, #0
	ret
.globl _boot_log_tick
.weak_definition _boot_log_tick
_boot_log_tick:
	mov	w0, #0
	ret
.globl _boot_process_capture
.weak_definition _boot_process_capture
_boot_process_capture:
	mov	w0, #0
	ret
.globl _boot_process_snapshot
.weak_definition _boot_process_snapshot
_boot_process_snapshot:
	mov	w0, #0
	ret
.globl _boot_ui_trace_snapshot
.weak_definition _boot_ui_trace_snapshot
_boot_ui_trace_snapshot:
	mov	w0, #0
	ret
.globl _boot_ui_trace_role_rows
.weak_definition _boot_ui_trace_role_rows
_boot_ui_trace_role_rows:
	mov	w0, #0
	ret
.globl _sheng_cpufreq_poll
.weak_definition _sheng_cpufreq_poll
_sheng_cpufreq_poll:
	mov	w0, #0
	ret
