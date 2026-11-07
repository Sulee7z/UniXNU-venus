// SPDX-License-Identifier: MIT
#pragma once
#ifdef __cplusplus
extern "C" {
#endif
#include "GeniSpi.h"
int vst_geni_message(struct geni_spi *,const uint8_t *,size_t,uint8_t *,size_t,unsigned,int *);
#ifdef __cplusplus
}
#endif
