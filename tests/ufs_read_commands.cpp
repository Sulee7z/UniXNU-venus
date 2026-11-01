// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <cstdint>
constexpr uint32_t kIOReturnUnsupported = 0xe00002c7;
#define NATIVE_UFS_BLOCK_READ_PROBE 1
#define main reference_commands_main
#include "RootCommands.cpp"
#undef main
int main()
{
  reset(); assert(ufs_test_nop() == 0);
  uint32_t value = 0, scsi = 0;
  assert(ufs_test_query(3, 2, &value) == 0);
  uint8_t capacity[10] = {0x25};
  assert(ufs_test_scsi(0, capacity, 10, true, 8, &scsi) == 0);
  uint8_t wake[6] = {0x1b, 0, 0, 0, 0x10, 0};
  assert(ufs_test_scsi(0xd0, wake, 6, false, 0, &scsi) == 0);
  std::array<uint8_t, 16384> out{};
  gVenusReadScope = {1, 4};
  assert(ufs_test_read(0, 1, 4, out.data()) == 0);
  reset(); gVenusReadScope = {};
  assert(ufs_test_read(0, 1, 1, out.data()) == kIOReturnUnsupported && writes == 0 && releases == 0);
  gVenusReadScope = {1, 1};
  assert(ufs_test_read(0, 2, 1, out.data()) == kIOReturnUnsupported);
  assert(ufs_test_read(1, 1, 1, out.data()) == kIOReturnUnsupported);
  for (unsigned op : {0x2aU, 0x35U, 0x04U, 0x42U, 0x48U, 0x3bU}) {
    uint8_t cdb[10] = {uint8_t(op)};
    assert(ufs_test_scsi(0, cdb, 10, false, 0, &scsi) == kIOReturnUnsupported);
  }
  wake[4] = 0x30;
  assert(ufs_test_scsi(0xd0, wake, 6, false, 0, &scsi) == kIOReturnUnsupported);
  assert(ufs_test_store_open(1, 4));
  assert(ufs_test_write(0, 1, 1, out.data()) == kIOReturnUnsupported);
  assert(ufs_test_sync() == kIOReturnUnsupported);
  assert(writes == 0 && releases == 0);
  for (Fault f : {Fault::Timeout, Fault::Empty, Fault::Lun, Fault::Residual, Fault::Fatal}) {
    reset(f); gVenusReadScope = {1, 1}; out.fill(0xa5);
    assert(ufs_test_read(0, 1, 1, out.data()) != 0 && out[0] == 0xa5);
    assertQuarantined();
  }
  puts("PASS: actual gated transport, exact read scope, write/format/flush refusal, optional ACTIVE wake and quarantine");
}
