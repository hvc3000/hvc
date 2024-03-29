#!/bin/sh

case "$1" in
start)

   if [ -e /var/run/dpow ]; then
   :

   else

   sudo mkdir /var/run/dpow
   sudo chown root:root /var/run/dpow

   fi

   if [ -e /var/run/dpow/nano-work-server.pid ] && [ -e /var/run/dpow/python3.pid ]; then
   echo NANO-dpow is already running

   else

        cd dpow-client/client

        bin/linux/nano-work-server --gpu 0:0 --gpu-local-work-size 64 -l 127.0.0.1:8000 &
        echo $!>/var/run/dpow/nano-work-server.pid

        python3 dpow_client.py --payout nano_3zo4anokuwhky77sy79tqghcny8qnfbxg3qg51thgoqphg7tss3i79agrwfq --work any &
        echo $!>/var/run/dpow/python3.pid
   fi
;;
stop)
    kill `cat /var/run/dpow/nano-work-server.pid`
    rm /var/run/dpow/nano-work-server.pid
    kill `cat /var/run/dpow/python3.pid`
    rm /var/run/dpow/python3.pid
   ;;

restart)
   $0 stop
   $0 start
   ;;

status)
   if [ -e /var/run/dpow/nano-work-server.pid ]; then
      echo nano-work-server is running, pid=`cat /var/run/dpow/nano-work-server.pid`
   else
      echo nano-work-server is NOT running
      exit 1
   fi
   ;;
*)
   echo "Usage: $0 {start|stop|status|restart}"
esac

exit 0      
