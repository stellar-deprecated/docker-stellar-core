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
