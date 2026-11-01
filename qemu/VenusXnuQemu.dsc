[Defines]
  PLATFORM_NAME = VenusXnuQemu
  PLATFORM_GUID = 36b681f1-9117-4199-9e16-3366cae64973
  PLATFORM_VERSION = 0.1
  DSC_SPECIFICATION = 0x0001001C
  OUTPUT_DIRECTORY = Build/VenusXnuQemu
  SUPPORTED_ARCHITECTURES = AARCH64
  BUILD_TARGETS = DEBUG|RELEASE
  SKUID_IDENTIFIER = DEFAULT
!include MdePkg/MdeLibs.dsc.inc
[LibraryClasses]
  BaseLib|MdePkg/Library/BaseLib/BaseLib.inf
  BaseMemoryLib|MdePkg/Library/BaseMemoryLib/BaseMemoryLib.inf
  DevicePathLib|MdePkg/Library/UefiDevicePathLib/UefiDevicePathLib.inf
  FdtLib|MdePkg/Library/BaseFdtLib/BaseFdtLib.inf
  MemoryAllocationLib|MdePkg/Library/UefiMemoryAllocationLib/UefiMemoryAllocationLib.inf
  PcdLib|MdePkg/Library/BasePcdLibNull/BasePcdLibNull.inf
  PrintLib|MdePkg/Library/BasePrintLib/BasePrintLib.inf
  UefiApplicationEntryPoint|MdePkg/Library/UefiApplicationEntryPoint/UefiApplicationEntryPoint.inf
  UefiBootServicesTableLib|MdePkg/Library/UefiBootServicesTableLib/UefiBootServicesTableLib.inf
  UefiDriverEntryPoint|MdePkg/Library/UefiDriverEntryPoint/UefiDriverEntryPoint.inf
  UefiLib|MdePkg/Library/UefiLib/UefiLib.inf
  UefiRuntimeServicesTableLib|MdePkg/Library/UefiRuntimeServicesTableLib/UefiRuntimeServicesTableLib.inf
  DebugPrintErrorLevelLib|MdePkg/Library/BaseDebugPrintErrorLevelLib/BaseDebugPrintErrorLevelLib.inf
  DebugLib|MdePkg/Library/UefiDebugLibStdErr/UefiDebugLibStdErr.inf
  UniXNULib|UniXNUPkg/Library/UniXNULib/UniXNULib.inf
[PcdsFixedAtBuild]
  gEfiMdePkgTokenSpaceGuid.PcdDebugPrintErrorLevel|0x80000000
  gEfiMdePkgTokenSpaceGuid.PcdDebugPropertyMask|0x07
[Components]
  UniXNUPkg/Application/UniXNU/UniXNU.inf
  DarwinBootPkg/Driver/DarwinBoot.inf
