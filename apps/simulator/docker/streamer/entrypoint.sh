#!/bin/sh

echo "*********************** RUNNING THE STREAMER ************************"
#get number of cpu cores in the system
nproc=$(nproc)

echo "*********************** Number of used cores for multiprocessing: $nproc ************************"

faststream run app/streamer/streamer:fast_stream  --workers $nproc