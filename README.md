# Example Voting App

A simple distributed application running across multiple Docker containers.

## Getting started

Download [Docker Desktop](https://www.docker.com/products/docker-desktop) for Mac or Windows. [Docker Compose](https://docs.docker.com/compose) will be automatically installed. On Linux, make sure you have the latest version of [Compose](https://docs.docker.com/compose/install/).

This solution uses Python, Node.js, .NET, with Redis for messaging and Postgres for storage.

Run in this directory to build and run the app:

```shell
docker compose up
```

The `vote` app will be running at [http://localhost:8080](http://localhost:8080), and the `results` will be at [http://localhost:8081](http://localhost:8081).

Alternately, if you want to run it on a [Docker Swarm](https://docs.docker.com/engine/swarm/), first make sure you have a swarm. If you don't, run:

```shell
docker swarm init
```

Once you have your swarm, in this directory run:

```shell
docker stack deploy --compose-file docker-stack.yml vote
```

## Run the app in Kubernetes

The folder k8s-specifications contains the YAML specifications of the Voting App's services.

Run the following command to create the deployments and services. Note it will create these resources in your current namespace (`default` if you haven't changed it.)

```shell
kubectl create -f k8s-specifications/
```

The `vote` web app is then available on port 31000 on each host of the cluster, the `result` web app is available on port 31001.

To remove them, run:

```shell
kubectl delete -f k8s-specifications/
```

## Kubernetes NetworkPolicies

The backend NetworkPolicies limit ingress to the database pods without changing application code or the existing Services:

- PostgreSQL pods (`app: db`) accept TCP `5432` only from worker (`app: worker`) and result (`app: result`) pods.
- Redis pods (`app: redis`) accept TCP `6379` only from vote (`app: vote`) and worker (`app: worker`) pods.

The policies use pod selectors only, so their source selectors apply within the namespace where the manifests are installed. They restrict only ingress to the selected backend pods; unrelated application traffic is not affected.

Apply or remove the policies:

```shell
kubectl apply -f k8s-specifications/db-network-policy.yaml
kubectl apply -f k8s-specifications/redis-network-policy.yaml

kubectl delete -f k8s-specifications/db-network-policy.yaml
kubectl delete -f k8s-specifications/redis-network-policy.yaml
```

Inspect them with:

```shell
kubectl get networkpolicies
kubectl describe networkpolicy allow-postgres-from-worker-and-result
kubectl describe networkpolicy allow-redis-from-vote-and-worker
```

To test enforcement, run temporary pods in the same namespace. An authorized source label should be able to open the matching backend port, while an unrecognized label should time out or be refused when the policy is enforced:

```shell
kubectl run redis-authorized --rm -it --restart=Never --image=busybox:1.36 --labels=app=vote -- sh -c 'nc -zvw 5 redis 6379'
kubectl run redis-unauthorized --rm -it --restart=Never --image=busybox:1.36 --labels=app=untrusted -- sh -c 'nc -zvw 5 redis 6379'

kubectl run db-authorized --rm -it --restart=Never --image=busybox:1.36 --labels=app=result -- sh -c 'nc -zvw 5 db 5432'
kubectl run db-unauthorized --rm -it --restart=Never --image=busybox:1.36 --labels=app=untrusted -- sh -c 'nc -zvw 5 db 5432'
```

NetworkPolicies take effect only with a CNI plugin that enforces them (for example, Calico or Cilium). Clusters without NetworkPolicy enforcement will accept the unauthorized connections despite these manifests.

## Architecture

![Architecture diagram](architecture.excalidraw.png)

* A front-end web app in [Python](/vote) which lets you vote between two options
* A [Redis](https://hub.docker.com/_/redis/) which collects new votes
* A [.NET](/worker/) worker which consumes votes and stores them in…
* A [Postgres](https://hub.docker.com/_/postgres/) database backed by a Docker volume
* A [Node.js](/result) web app which shows the results of the voting in real time

## Notes

The voting application only accepts one vote per client browser. It does not register additional votes if a vote has already been submitted from a client.

This isn't an example of a properly architected perfectly designed distributed app... it's just a simple
example of the various types of pieces and languages you might see (queues, persistent data, etc), and how to
deal with them in Docker at a basic level.
