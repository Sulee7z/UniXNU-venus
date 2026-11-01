// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <vector>
#include "VenusUfsGptRead.h"
int main(int argc, char **argv)
{
  assert(argc == 4);
  auto load = [](const char *path) {
    std::ifstream input(path, std::ios::binary);
    assert(input);
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(input), {});
  };
  auto primary = load(argv[1]), backup = load(argv[2]);
  uint64_t last = std::strtoull(argv[3], nullptr, 0);
  assert(primary.size() % 4096 == 0 && backup.size() % 4096 == 0);
  uint64_t backupStart = last + 1 - backup.size() / 4096;
  std::array<uint8_t, 32768> scratch{};
  auto result = VenusUfsGptRead::collect(4096, last, scratch.data(), scratch.size(),
    [&](uint64_t lba, unsigned blocks, uint8_t *out) {
      assert(blocks && blocks <= 4);
      if (lba < primary.size()/4096 && blocks <= primary.size()/4096-lba) {
        memcpy(out, primary.data()+lba*4096, blocks*4096); return true;
      }
      assert(lba >= backupStart && lba <= last && blocks <= last+1-lba);
      memcpy(out, backup.data()+(lba-backupStart)*4096, blocks*4096); return true;
    });
  if (result.error) { std::fprintf(stderr,"%s\n",result.error); return 1; }
  assert(result.used == 34);
  std::printf("PASS: actual retained Venus GPT, %u entries/%u used, %u reads, header CRC %08x/%08x array %08x\n",
              result.entries,result.used,result.reads,result.primaryCrc,result.backupCrc,result.entriesCrc);
}
