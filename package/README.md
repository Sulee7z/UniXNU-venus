# Venus board package

The format-2 build tree maps this directory to `kits/venus`. UFS/root,
legacy CPU display and offline AKS/HID services are integrated at their
recorded qualification levels. Physical touch/buttons and backlight still use
inactive board hooks. Current component selection is in board.toml.

`boot-progress/BootDataCheck*.h` provides the opt-in Data file qualification
before launchd. Its first cross-reboot test failed; `../DATA-PUBLICATION.md`
records the persistent disk publication-order correction and host checks.
`../DISPLAY-INPUT-FOUNDATION.md` records the next display/input prerequisites.
