/** @file
  Publish the FAT initrd from a Mu-Silicium FDT handoff as a read-only block device.

  SPDX-License-Identifier: BSD-2-Clause
**/

#include <Uefi.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/DebugLib.h>
#include <Library/FdtLib.h>
#include <Library/PrintLib.h>
#include "../../Include/Guid/UniXNURamDiskStatus.h"
#include <Library/HobLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Protocol/BlockIo.h>
#include <Protocol/DevicePath.h>

// Mu-Silicium SEC stores the incoming x0 value in this HOB as a UINT64.
STATIC CONST EFI_GUID mEntryArgHobGuid = {
  0xDAEE82E6, 0x8090, 0x4E72, { 0xBF, 0xB9, 0x78, 0xC1, 0x3C, 0xD4, 0xE3, 0x59 }
};

STATIC
UINT64
ReadCells (
  IN CONST VOID  *Data,
  IN UINT32      Cells
  )
{
  if (Cells == 2) {
    return Fdt64ToCpu (ReadUnaligned64 (Data));
  }

  return Fdt32ToCpu (ReadUnaligned32 (Data));
}

#define RAM_BLOCK_SIZE  512

#pragma pack(1)
typedef struct {
  VENDOR_DEVICE_PATH          Vendor;
  EFI_DEVICE_PATH_PROTOCOL    End;
} RAM_BLOCK_DEVICE_PATH;
#pragma pack()

STATIC RAM_BLOCK_DEVICE_PATH  mDevicePath = {
  {
    { HARDWARE_DEVICE_PATH, HW_VENDOR_DP, { (UINT8)sizeof (VENDOR_DEVICE_PATH), (UINT8)(sizeof (VENDOR_DEVICE_PATH) >> 8) } },
    { 0xA9C6827C, 0x1BD8, 0x410C, { 0x88, 0x5A, 0xC4, 0x65, 0x00, 0xF7, 0xD8, 0x36 } }
  },
  { END_DEVICE_PATH_TYPE, END_ENTIRE_DEVICE_PATH_SUBTYPE, { sizeof (EFI_DEVICE_PATH_PROTOCOL), 0 } }
};

STATIC CONST EFI_GUID mStatusGuid = UNIXNU_RAM_DISK_STATUS_GUID;
STATIC UNIXNU_RAM_DISK_STATUS mStatus = { 1, "RAM disk driver entered" };

// Do not dereference an incoming range outside the firmware memory map.
STATIC BOOLEAN MemoryCovered (UINT64 Base, UINT64 Length)
{
  EFI_MEMORY_DESCRIPTOR *Map = NULL;
  UINTN Size = 0, Key, Stride = 0, At;
  UINT32 Version;
  EFI_STATUS Status;
  UINT64 Cursor, End, Next;
  if (Base == 0 || Length == 0 || Base > MAX_UINT64 - Length) { return FALSE; }
  Status = gBS->GetMemoryMap (&Size, Map, &Key, &Stride, &Version);
  if (Status != EFI_BUFFER_TOO_SMALL || Size > SIZE_1MB) { return FALSE; }
  Size += EFI_PAGE_SIZE;
  Status = gBS->AllocatePool (EfiBootServicesData, Size, (VOID **)&Map);
  if (EFI_ERROR (Status)) { return FALSE; }
  Status = gBS->GetMemoryMap (&Size, Map, &Key, &Stride, &Version);
  if (EFI_ERROR (Status) || Stride < sizeof (*Map)) { gBS->FreePool (Map); return FALSE; }
  Cursor = Base;
  End = Base + Length;
  while (Cursor < End) {
    Next = Cursor;
    for (At = 0; At + Stride <= Size; At += Stride) {
      EFI_MEMORY_DESCRIPTOR *D = (EFI_MEMORY_DESCRIPTOR *)((UINT8 *)Map + At);
      UINT64 Bytes;
      if (D->NumberOfPages > (MAX_UINT64 >> EFI_PAGE_SHIFT)) { continue; }
      Bytes = D->NumberOfPages << EFI_PAGE_SHIFT;
      if (D->PhysicalStart > MAX_UINT64 - Bytes) { continue; }
      if (D->PhysicalStart <= Cursor && Cursor < D->PhysicalStart + Bytes && D->PhysicalStart + Bytes > Next) {
        Next = D->PhysicalStart + Bytes;
      }
    }
    if (Next == Cursor) { gBS->FreePool (Map); return FALSE; }
    Cursor = Next;
  }
  gBS->FreePool (Map);
  return TRUE;
}

STATIC UINT8                    *mRamBase;
STATIC EFI_BLOCK_IO_MEDIA       mMedia;

STATIC
EFI_STATUS
EFIAPI
RamBlockReset (
  IN EFI_BLOCK_IO_PROTOCOL  *This,
  IN BOOLEAN                ExtendedVerification
  )
{
  return EFI_SUCCESS;
}

STATIC
EFI_STATUS
EFIAPI
RamBlockRead (
  IN  EFI_BLOCK_IO_PROTOCOL  *This,
  IN  UINT32                 MediaId,
  IN  EFI_LBA                Lba,
  IN  UINTN                  BufferSize,
  OUT VOID                   *Buffer
  )
{
  if (Buffer == NULL) {
    return EFI_INVALID_PARAMETER;
  }

  if (MediaId != mMedia.MediaId) {
    return EFI_MEDIA_CHANGED;
  }

  if ((BufferSize % RAM_BLOCK_SIZE) != 0) {
    return EFI_BAD_BUFFER_SIZE;
  }

  if ((Lba > mMedia.LastBlock) || ((BufferSize / RAM_BLOCK_SIZE) > (mMedia.LastBlock + 1 - Lba))) {
    return EFI_INVALID_PARAMETER;
  }

  CopyMem (Buffer, mRamBase + Lba * RAM_BLOCK_SIZE, BufferSize);
  return EFI_SUCCESS;
}

STATIC
EFI_STATUS
EFIAPI
RamBlockWrite (
  IN EFI_BLOCK_IO_PROTOCOL  *This,
  IN UINT32                 MediaId,
  IN EFI_LBA                Lba,
  IN UINTN                  BufferSize,
  IN VOID                   *Buffer
  )
{
  return EFI_WRITE_PROTECTED;
}

STATIC
EFI_STATUS
EFIAPI
RamBlockFlush (
  IN EFI_BLOCK_IO_PROTOCOL  *This
  )
{
  return EFI_SUCCESS;
}

STATIC EFI_BLOCK_IO_PROTOCOL  mBlockIo = {
  EFI_BLOCK_IO_PROTOCOL_REVISION,
  &mMedia,
  RamBlockReset,
  RamBlockRead,
  RamBlockWrite,
  RamBlockFlush
};

STATIC
VOID
PublishInitrd (
  IN CONST VOID  *Fdt
  )
{
  EFI_STATUS  Status;
  INT32       Chosen;
  CONST VOID  *StartProp;
  CONST VOID  *EndProp;
  INT32       StartLength;
  INT32       EndLength;
  UINT64      Start;
  UINT64      End;
  EFI_HANDLE  Handle;

  Chosen = FdtPathOffset (Fdt, "/chosen");
  if (Chosen < 0) {
    AsciiSPrint (mStatus.Message, sizeof (mStatus.Message), "FDT has no /chosen");
    DEBUG ((DEBUG_ERROR, "UNIXNURAMDISK: no /chosen\n"));
    return;
  }

  StartProp = FdtGetProp (Fdt, Chosen, "linux,initrd-start", &StartLength);
  EndProp   = FdtGetProp (Fdt, Chosen, "linux,initrd-end", &EndLength);
  if ((StartProp == NULL) || (EndProp == NULL) ||
      ((StartLength != 4) && (StartLength != 8)) || ((EndLength != 4) && (EndLength != 8)))
  {
    AsciiSPrint (mStatus.Message, sizeof (mStatus.Message), "FDT has no initrd range");
    DEBUG ((DEBUG_ERROR, "UNIXNURAMDISK: no initrd in /chosen\n"));
    return;
  }

  Start = ReadCells (StartProp, StartLength / 4);
  End   = ReadCells (EndProp, EndLength / 4);
  if ((End <= Start) || (((End - Start) % RAM_BLOCK_SIZE) != 0)) {
    AsciiSPrint (mStatus.Message, sizeof (mStatus.Message), "initrd unaligned %lx-%lx", Start, End);
    DEBUG ((DEBUG_ERROR, "UNIXNURAMDISK: initrd 0x%lx-0x%lx is not a whole number of sectors\n", Start, End));
    return;
  }

  if (!MemoryCovered (Start, End - Start)) {
    AsciiSPrint (mStatus.Message, sizeof (mStatus.Message), "initrd outside memory map %lx-%lx", Start, End);
    return;
  }
  mRamBase                = (UINT8 *)(UINTN)Start;
  mMedia.MediaId          = 1;
  mMedia.RemovableMedia   = FALSE;
  mMedia.MediaPresent     = TRUE;
  mMedia.LogicalPartition = FALSE;
  mMedia.ReadOnly         = TRUE;
  mMedia.WriteCaching     = FALSE;
  mMedia.BlockSize        = RAM_BLOCK_SIZE;
  mMedia.IoAlign          = 1;
  mMedia.LastBlock        = (End - Start) / RAM_BLOCK_SIZE - 1;

  Handle = NULL;
  Status = gBS->InstallMultipleProtocolInterfaces (
                  &Handle,
                  &gEfiDevicePathProtocolGuid,
                  &mDevicePath,
                  &gEfiBlockIoProtocolGuid,
                  &mBlockIo,
                  NULL
                  );
  AsciiSPrint (mStatus.Message, sizeof (mStatus.Message), "block %r %lx+%lx magic=%08x", Status, Start, End - Start, ReadUnaligned32 ((CONST UINT32 *)mRamBase));
  DEBUG ((DEBUG_ERROR, "UNIXNURAMDISK: initrd block device 0x%lx size 0x%lx %r\n", Start, End - Start, Status));
}

EFI_STATUS
EFIAPI
UniXNURamDiskDxeEntry (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  EFI_HOB_GUID_TYPE  *Hob;
  UINT64             Dtb;

  gBS->InstallConfigurationTable ((EFI_GUID *)&mStatusGuid, &mStatus);
  Hob = GetFirstGuidHob (&mEntryArgHobGuid);
  if (Hob == NULL) {
    AsciiSPrint (mStatus.Message, sizeof (mStatus.Message), "entry argument HOB missing");
    DEBUG ((DEBUG_ERROR, "UNIXNURAMDISK: no entry argument HOB\n"));
    return EFI_SUCCESS;
  }

  if (GET_GUID_HOB_DATA_SIZE (Hob) < sizeof (UINT64)) {
    AsciiSPrint (mStatus.Message, sizeof (mStatus.Message), "entry argument HOB truncated");
    return EFI_COMPROMISED_DATA;
  }

  Dtb = ReadUnaligned64 ((CONST UINT64 *)GET_GUID_HOB_DATA (Hob));
  if ((Dtb & 3) != 0 || !MemoryCovered (Dtb, 40)) {
    AsciiSPrint (mStatus.Message, sizeof (mStatus.Message), "FDT outside memory map x0=%lx", Dtb);
    return EFI_SUCCESS;
  }
  if (FdtCheckHeader ((VOID *)(UINTN)Dtb) != 0) {
    AsciiSPrint (mStatus.Message, sizeof (mStatus.Message), "invalid FDT x0=%lx", Dtb);
    DEBUG ((DEBUG_ERROR, "UNIXNURAMDISK: x0 0x%lx is not a device tree\n", Dtb));
    return EFI_SUCCESS;
  }

  DEBUG ((DEBUG_ERROR, "UNIXNURAMDISK: device tree at 0x%lx, %u bytes\n", Dtb, (UINT32)FdtTotalSize ((VOID *)(UINTN)Dtb)));

  if (FdtTotalSize ((VOID *)(UINTN)Dtb) > SIZE_2MB ||
      !MemoryCovered (Dtb, FdtTotalSize ((VOID *)(UINTN)Dtb))) {
    AsciiSPrint (mStatus.Message, sizeof (mStatus.Message), "FDT extent unavailable x0=%lx", Dtb);
    return EFI_SUCCESS;
  }
  PublishInitrd ((VOID *)(UINTN)Dtb);
  return EFI_SUCCESS;
}
