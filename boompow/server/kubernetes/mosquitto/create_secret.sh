#!/bin/bash
kubectl create secret generic passwd --from-file=passwd -n mosquitto