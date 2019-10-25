#!/bin/bash

if (( $# != 1)) then
    echo "$0 logfile"
    exit -1
fi

logFile=$1
netDevName="eth0"

exec 2>&1 1> $logFile

show(){
    echo $*
    $*
}


show ifconfig $netDevName
show ethtool $netDevName
show ethtool -i $netDevName
show ethtool -k $netDevName
show ethtool -S $netDevName
show netstat -s
show dmesg

#######fixed information#######
# show cat /proc/uptime
# show cat /proc/version
# show sysctl -a

# show cat /proc/cpuinfo
# show lsmod
# show mount

#######realtime information#######

#physical memory fragment debug information
# show cat /proc/buddyinfo
# show cat /proc/loadavg
# show cat /proc/meminfo
# show cat /proc/pagetypeinfo

# show cat /proc/vmstat

# show cat /proc/slabinfo

#######accumulated information#######

#nreads/merged nreads/read nsectors/milliseconds spent on all reads/
#nwrites/merged nwrites/write nsectors/milliseconds spent on all writes/
#nIOs in progress/milliseconds spent on doing IOs/another milliseconds spent on doing IOs/
show cat /proc/diskstats

show cat /proc/interrupts

irqs=`cat /proc/interrupts|grep $netDevName|cut -f1 -d:|xargs`
for i in $irqs; do
    show cat /proc/irq/$i/spurious
    show cat /proc/irq/$i/smp_affinity
done

show cat /proc/softirqs


show cat /proc/sched_debug
show cat /proc/schedstat

#user/nice/system/idle/iowait/irq/softirq
#procs_blocked: nr_of_tasks_in_iowait
show cat /proc/stat

nginx=`pidof nginx`
for i in $nginx; do
    #syscr/syscw/read_bytes/write_bytes/
    show cat /proc/$i/io

    #se.statistics.iowait_sum/se.nr_migrations/se.sum_exec_runtime/se.vruntime
    show cat /proc/$i/sched

    #time spent on cpu/time spent waiting on runqueue/# of timeslices
    show cat /proc/$i/schedstat

    #.../utime/stime/starttime/(42)delayacct_blkio_ticks/
    show cat /proc/$i/stat


    show cat /proc/$i/statm

    #../VmPeak/VmHWM
    show cat /proc/$i/status
done
    
# show cat /proc/mpt/*
# show cat /proc/net/*

show cat /proc/fs/ext4/dm-0/es_shrinker_info
show cat /proc/fs/ext4/dm-0/options
show cat /proc/fs/ext4/dm-0/mb_groups

show cat /proc/fs/ext4/dm-1/es_shrinker_info
show cat /proc/fs/ext4/dm-1/options
show cat /proc/fs/ext4/dm-1/mb_groups

show cat /proc/fs/jbd2/dm-0-8/info
show cat /proc/fs/jbd2/dm-1-8/info
