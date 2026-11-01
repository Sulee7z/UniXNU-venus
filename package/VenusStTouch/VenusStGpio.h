// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>

// pinctrl-lahaina.c: CTL mux[5:2], drive[8:6], OE[9]; IO IN[0], OUT[1].
// IN is a sampled level, not a writable input-enable bit.
static inline uint32_t vst_gpio_control(uint32_t old,unsigned mux,unsigned drive,unsigned pull,int output) {
    return (old&~0x3ffu)|((mux&15u)<<2)|((drive&7u)<<6)|(pull&3u)|(output?1u<<9:0);
}
static inline uint32_t vst_gpio_output(uint32_t old,int high) {
    return (old&~2u)|(high?2u:0);
}
