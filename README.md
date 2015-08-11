# stellar-core

Docker definitions for [stellar-core](https://github.com/stellar/stellar-core)

# Usage


## A local full network

This starts a 3 node local stellar-core network, all on the same docker host.

Note that the provided local.env uses SDF S3 locations, so edit it to match the specifics of your environment.

```sh
for N in 1 2; do
  docker run --name db$N -p 544$N:5432 --env-file examples/local.env -d stellar/stellar-core-state
  docker run --name node$N --net host -v ~/.aws:/root/.aws --volumes-from db$N --env-file examples/local.env -d stellar/stellar-core /start node$N fresh forcescp
done

for N in 3; do
  docker run --name db$N -p 544$N:5432 --env-file examples/local.env -d stellar/stellar-core-state
  docker run --name node$N --net host -v ~/.aws:/root/.aws --volumes-from db$N --env-file examples/local.env -d stellar/stellar-core /start node$N fresh
done
```

The use of `-v ~/.aws:/root/.aws` here mounts your local aws credentials into the container which allows the network to use S3 for storage.

You can check the cluster status with curl. The IP shown here is a typical boot2docker IP. Replace it with the IP of your docker host.

```sh
watch 'echo 6 7 3 | xargs -n1 -I{} curl -s 192.168.59.103:1162{}/info'
```

Basic clean up involves simply wiping out all containers. S3 history must be removed seperately. Something like this should do the trick.

```sh
docker ps -a | egrep '(node|db)\d+' | awk '{ print $1 }' | xargs -n1 docker rm -f -v
```

## Single node configurations

> **NOTE:** The commands below are pinned to version 0.0.1-62-5f94fa02 to match testnet.
> 
> This is to avoid key format issues following the merge of https://github.com/stellar/stellar-core/pull/619. This tag should be removed once testnet is updated.

### Catch up complete with SDF testnet

```
docker run --name db_compat_complete -p 5541:5432 --env-file examples/compat_complete.env -d stellar/stellar-core-state
docker run --name compat_complete --net host --volumes-from db_compat_complete --env-file examples/compat_complete.env -d stellar/stellar-core:0.0.1-62-5f94fa02 /start compat_complete fresh
```

### Catch up minimal with SDF testnet

```
docker run --name db_compat_minimal -p 5641:5432 --env-file examples/compat_minimal.env -d stellar/stellar-core-state
docker run --name compat_minimal --net host --volumes-from db_compat_minimal --env-file examples/compat_minimal.env -d stellar/stellar-core:0.0.1-62-5f94fa02 /start compat_minimal fresh
```

### Single node local network (with monitoring)

Note that the monitoring container is invoked with the docker socket exposed. This allows the monitoring container to invoke `docker run stellar/stellar-core` to do things like process core dumps.

```
docker run --name single-state \
           -p 5432:5432 \
           --env-file examples/single.env \
           -d stellar/stellar-core-state

docker run --name single \
           --net host \
           --volumes-from single-state \
           -v /volumes/main/cores:/cores -v /volumes/main/logs:/logs \
           --env-file examples/single.env \
           -d stellar/stellar-core \
           /start main fresh forcescp

# optionally
docker run --name single-heka \
           --net container:single \
           --volumes-from single \
           -v /var/run/docker.sock:/var/run/docker.sock \
           --env-file examples/single.env \
           -d stellar/heka
```

## A note on capturing core files

Capturing core files from container process is a bit involved.

You'll need to first enable unlimited sized core dumps at the docker layer, then set a `core_pattern` to a location that the container has set up as a volume.

If either are not set, the core will not be dumped.

If you're on boot2docker you can set this by adding the following to the boot2docker profile:

```sh
echo '/cores/%e_%h_%s_%p_%t.core' > /proc/sys/kernel/core_pattern
EXTRA_ARGS="--default-ulimit core=-1"
```

To edit this profile use the following commands to first edit the file, then restart the docker daemon:

```console
> boot2docker ssh -t sudo vi /var/lib/boot2docker/profile
> boot2docker ssh 'sudo /etc/init.d/docker restart'
```

On docker-machine you can specify engine options when creating the machine, then use ssh to set the core pattern:

```console
> docker-machine create \
    --driver virtualbox \
    --engine-opt 'default-ulimit=core=-1' core1
> docker-machine ssh core1 \
    "sudo sh -c 'echo \"/cores/%e_%h_%s_%p_%t.core\" > /proc/sys/kernel/core_pattern'"
```

