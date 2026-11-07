/* SPDX-License-Identifier: BSD-2-Clause-Patent */
/*
 * Source for the machine routines that xnu-12377 only ships as
 * machine_routines_nos.o in the KDK KernelSupport archives
 * (lib<SoC>.os.<config>.a). Behaviour follows the T8101 object of the
 * macOS 26.5.2 (25F84) KDK, without its Apple SPRR programming.
 */
#include <arm/machine_routines.h>
#include <pexpert/device_tree.h>

boolean_t
ml_device_is_prod_fused(void)
{
	DTEntry chosen = NULL;
	void const *value = NULL;
	unsigned int size = 0;

	if (SecureDTLookupEntry(NULL, "/chosen", &chosen) != kSuccess) {
		return FALSE;
	}
	if (SecureDTGetProperty(chosen, "certificate-production-status", &value, &size) != kSuccess ||
	    size != sizeof(uint32_t)) {
		return FALSE;
	}
	return *(uint32_t const *)value;
}

/* SIQ is an SPTM-platform interrupt facility; arm_init_sptm.c is its only caller. */
void
siq_init(void)
{
}

void
siq_cpu_init(void)
{
}
