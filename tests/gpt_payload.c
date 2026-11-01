// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t UINT8;
typedef uint32_t UINT32;
typedef uint64_t UINT64;
typedef int BOOLEAN;
#define STATIC static
#define CONST const
#define TRUE 1
#define FALSE 0
#define CompareMem memcmp
#include "VenusFatView.h"
static UINT64 header(const char *path, UINT8 bytes[512])
{
  FILE *f = fopen(path, "rb"); long size;
  assert(f && fread(bytes, 1, 512, f) == 512);
  assert(fseek(f, 0, SEEK_END) == 0); size = ftell(f); assert(size > 0); fclose(f);
  return (UINT64)size;
}
int main(int argc, char **argv)
{
  UINT8 bytes[512], bad[512]; UINT64 size, found = 0;
  assert(argc == 2 || argc == 3);
  size = header(argv[1], bytes);
  assert(VenusFatView(bytes, size, &found) && found == size);
  assert(!VenusFatView(bytes, size - 1, &found));
  memcpy(bad, bytes, 512);
  memcpy(bad + 71, "VENUSGPT   ", 11); memset(bad + 43, 0, 11);
  assert(!VenusFatView(bad, size, &found));
  for (unsigned offset = 0; offset < 512; ++offset) {
    UINT8 *copy = malloc(offset + 512); assert(copy);
    memcpy(copy + offset, bytes, 512);
    assert(VenusFatView(copy + offset, size, &found)); free(copy);
  }
  if (argc == 3) {
    size = header(argv[2], bad);
    assert(!VenusFatView(bad, size, &found));
  }
  puts("PASS: exact board FAT recognizer accepts corrected payload; old VENUSGPT label refuses; all alignment offsets bounded");
}
