#!/bin/sh

case "$1" in
start)

   if [ -e /var/run/bpow ]; then
   :

   else

   sudo mkdir /var/run/bpow
   sudo chown root:root /var/run/bpow

   fi

   if [ -e /var/run/bpow/nano-work-server.pid ] && [ -e /var/run/bpow/python3.pid ]; then
   echo boompow is already running

   else

        cd boompow/client

        bin/linux/nano-work-server --gpu 0:0 --gpu-local-work-size 64 -l 127.0.0.1:7000 &
        echo $!>/var/run/bpow/nano-work-server.pid

        python3 bpow_client.py --payout ban_1qtjxpycspr5zzq66p4gf3h9t97rq7f9q4gu9buyhr8zgmi73j3aym9t6aun --async_mode --limit_logging -work any
        echo $!>/var/run/bpow/python3.pid
   fi
;;
stop)


    kill `cat /var/run/bpow/nano-work-server.pid`
    rm /var/run/bpow/nano-work-server.pid
    kill `cat /var/run/bpow/python3.pid`
    rm /var/run/bpow/python3.pid
   ;;

restart)
   $0 stop
   $0 start
   ;;

status)
   if [ -e /var/run/bpow/nano-work-server.pid ]; then
      echo nano-work-server is running, pid=`cat /var/run/bpow/nano-work-server.pid
   else
      echo nano-work-server is NOT running

   fi

   if [ -e /var/run/bpow/python3.pid ]; then
      echo bpow_client is running, pid=`cat /var/run/bpow/python3.pid`
   else
      echo bpow_client is NOT running
      exit 1
   fi
   ;;
*)
   echo "Usage: $0 {start|stop|status|restart}"
esac

exit 0
