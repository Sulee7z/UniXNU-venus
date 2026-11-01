// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
namespace VenusUfsReadCommands {
struct Scope { uint64_t first = 0; uint32_t blocks = 0; };
inline bool allowed(const Scope &scope, uint8_t lun, const uint8_t *cdb, unsigned n, unsigned direction, uint32_t bytes)
{
  if (!cdb || !n || direction == 1) return false;
  if (cdb[0] == 0 || cdb[0] == 0x25 || cdb[0] == 0x1b) {
    unsigned size = cdb[0] == 0x25 ? 10 : 6;
    bool capacity = cdb[0] == 0x25, wake = cdb[0] == 0x1b;
    if (n != size || lun != (wake ? 0xd0 : 0) || direction != (capacity ? 2U : 0U) || bytes != (capacity ? 8U : 0U)) return false;
    for (unsigned i = 1; i < n; ++i) if (cdb[i] != (wake && i == 4 ? 0x10 : 0)) return false;
    return true;
  }
  if (cdb[0] != 0x28 || n != 10 || lun || direction != 2 || cdb[1] || cdb[6] || cdb[9] ||
      !scope.blocks || scope.blocks > 4 || scope.first > 0xffffffffULL - (scope.blocks - 1)) return false;
  uint32_t lba = uint32_t(cdb[2]) << 24 | uint32_t(cdb[3]) << 16 | uint32_t(cdb[4]) << 8 | cdb[5];
  return lba == scope.first && ((uint32_t(cdb[7]) << 8) | cdb[8]) == scope.blocks && bytes == scope.blocks * 4096;
}
}
