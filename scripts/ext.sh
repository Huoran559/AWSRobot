#!/bin/bash
dirname=0
for file in ./*.tar.gz
do
    if [[ -f $file ]]; then
	echo $file $dirname
	rm -rf $dirname
        tar -zxvf $file
        rawformat --flagsurl /home/ec2-user/cpu2006-test/config/flags/gcc4x.xml --output_format all ./result/CINT2006.001.ref.rsf
        rawformat --flagsurl /home/ec2-user/cpu2006-test/config/flags/gcc4x.xml --output_format all ./result/CFP2006.001.ref.rsf
	mv result $dirname
	let dirname=$dirname+1
    fi
done
