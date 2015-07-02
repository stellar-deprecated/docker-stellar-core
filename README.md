## Core files

Capturing core files from container process is a bit interesting. You'll need to first enable unlimited sized core dumps at the docker layer, then set a `core_pattern` to a location that the container has set up as a volume.

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

## Full network

This one is still a little complex to get running, these are the basics:

* make an env file for the cluster similar to `examples/local.env`

* start the cluster

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

* check cluster status

```sh
watch 'echo 1 2 3 | xargs -n1 -I{} curl -s 192.168.59.103:3915{}/info'
```

* Clean up the cluster

```sh
# Clean up all containers
docker ps -a | egrep '(node|db)\d+' | awk '{ print $1 }' | xargs -n1 docker rm -f -v
```

## Single peer tests

Catch up complete

```
docker run --name db_compat_complete -p 5541:5432 --env-file examples/compat_complete.env -d stellar/stellar-core-state
docker run --name compat_complete --net host --volumes-from db_compat_complete --env-file examples/compat_complete.env -d stellar/stellar-core /start compat_complete fresh
```

Catch up minimal

```
docker run --name db_compat_minimal -p 5641:5432 --env-file examples/compat_minimal.env -d stellar/stellar-core-state
docker run --name compat_minimal --net host --volumes-from db_compat_minimal --env-file examples/compat_minimal.env -d stellar/stellar-core /start compat_minimal fresh
```

Single node local network (with monitoring). Note that the monitoring container is invoked with the docker socket exposed. This allows us to invoke `docker run stellar/stellar-core` to do things like process core dumps.

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
           /start main fresh

docker run --name single-heka \
           --net container:single \
           --volumes-from single \
           -v /var/run/docker.sock:/var/run/docker.sock \
           --env-file examples/single.env \
           -d stellar/heka
```
