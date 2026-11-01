// SPDX-License-Identifier: BSD-2-Clause-Patent
#define main reference_commands_main
#include "RootCommands.cpp"
#undef main
int main()
{
  assert(reference_commands_main() == 0);
  reset(); assert(ufs_test_store_open(100, 8));
  std::array<uint8_t,4096> data; data.fill(0x4b);
  std::array<uint8_t,kDmaBytes> before; memcpy(before.data(), memory, sizeof(memory));
  callback = [](unsigned op, uint64_t address, uint64_t value, void *bytes) -> uint64_t {
    if (op == 6) { gHost.poisoned = true; gHost.ready = false; return 0; }
    return io(op, address, value, bytes);
  };
  assert(ufs_test_write(0, 100, 1, data.data()) == kIOReturnNotReady);
  assert(writes == 0 && releases == 0 && !memcmp(before.data(), memory, sizeof(memory)));
  reset(); assert(ufs_test_store_open(100, 8));
  assert(ufs_test_write(0, 99, 1, data.data()) == kIOReturnBadArgument);
  assert(ufs_test_write(0, 108, 1, data.data()) == kIOReturnBadArgument && writes == 0);
  puts("PASS: root write window bounds and quarantine after lock acquisition, with no poisoned DMA modification");
}
