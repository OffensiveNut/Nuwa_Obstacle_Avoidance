#!/bin/sh
# 
#  @file      run_ascam.sh
#  @brief     run angstrong acamera script
#
#  Copyright (c) 2022 Angstrong Tech.Co.,Ltd
#
#  @author    Angstrong SDK develop Team
#  @date      2022/04/22
#  @version   1.0
#

gcc_target=$(gcc -v 2>&1 | grep Target: | sed 's/Target: //g')

# Map gcc target to lib directory name
case "$gcc_target" in
    x86_64-pc-linux-gnu)
        lib_arch="x86_64-linux-gnu"
        ;;
    *aarch64*)
        lib_arch="aarch64-linux-gnu"
        ;;
    *arm*)
        lib_arch="arm-linux-gnueabihf"
        ;;
    *)
        lib_arch="$gcc_target"
        ;;
esac

CUR_DIR=$(dirname "$(readlink -f "$0")")
cd $CUR_DIR/libs/lib/${lib_arch}
# libPath=$(dirname $(readlink -f "$0"))
libPath=$(pwd)
export LD_LIBRARY_PATH=$libPath:$LD_LIBRARY_PATH
echo "lib path:"${libPath}

log_file=AngstrongsdkLog.txt

cd $CUR_DIR/build/
sudo env LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$libPath ./ascamera 2>&1 | tee $log_file
