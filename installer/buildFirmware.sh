#!/bin/bash
rm -rf build
mkdir build
rm -rf firmware
mkdir firmware
cd firmware
mkdir maslowcnc
mkdir holey

cd ../..

maslowcnc_firmware_repo=https://github.com/MaslowCNC/Firmware.git
maslowcnc_firmware_sha=e1e0d020fff1f4f7c6b403a26a85a16546b7e15b
git clone $maslowcnc_firmware_repo firmware/maslowcnc
cd firmware/maslowcnc
git checkout $maslowcnc_firmware_sha
pio lib install "Servo"
pio run -e megaatmega2560
mv .pio/build/megaatmega2560/firmware.hex ./maslowcnc-$(sed -n -e 's/^.*VERSIONNUMBER //p' cnc_ctrl_v1/Maslow.h).hex

cd ../..

holey_firmware_repo=https://github.com/WebControlCNC/Firmware.git
holey_firmware_sha=950fb23396171cbd456c2d4149455cc45f5e6bc3
git clone $holey_firmware_repo firmware/holey
cd firmware/holey
git checkout $holey_firmware_sha
pio run -e megaatmega2560
mv .pio/build/megaatmega2560/firmware.hex ./holey-$(sed -n -e 's/^.*VERSIONNUMBER //p' cnc_ctrl_v1/Maslow.h).hex