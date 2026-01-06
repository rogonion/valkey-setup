# valkey-setup

A utility for creating a customized, rootless [Valkey](https://valkey.io/) container image with the option
of including compiled modules (extensions) like JSON, Search, and Bloom filters.

**Base Image:** [openSUSE Leap 16.0](https://registry.opensuse.org/cgi-bin/cooverview)  
**Valkey Version:** 9.0.1 (Compiled from source)

## Pre-requisites

**OS:** Linux-based.

<table>
    <caption>Required Tools</caption>
    <thead>
        <tr>
            <th>Package</th>
            <th>Version</th>
            <th>Notes</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Python</td>
            <td>3.13+</td>
            <td>
                <p>Core language the CLI tool is written in.</p>
            </td>
        </tr>
        <tr>
            <td><a href="https://python-poetry.org/docs/">Poetry</a></td>
            <td>2.2.1+</td>
            <td>
                <p>Project dependency manager.</p>
            </td>
        </tr>
        <tr>
            <td><a href="https://buildah.io/">Buildah</a></td>
            <td>1.41.5+</td>
            <td>
                <p>Used to programmatically create OCI-compliant container images without a daemon.</p>
            </td>
        </tr>
        <tr>
            <td><a href="https://taskfile.dev/">Taskfile</a></td>
            <td>3.46.3+</td>
            <td>
                <p>Optional. You can use the provided <a href="taskw">shell script wrapper</a> (<code>./taskw</code>) which scopes the binary to the project.</p>
            </td>
        </tr>
    </tbody>
</table>

## Usage

List available tasks:

```shell
./taskw --list
```

Setup python virtual environment and install dependencies:

```shell
TASKFILE_BINARY="./taskw"

$TASKFILE_BINARY init
```

View CLI tool options and build help:

```shell
TASKFILE_BINARY="./taskw"

$TASKFILE_BINARY run -- --help
```

### Example

Build valkey core binary from source:

```shell
TASKFILE_BINARY="./taskw"

$TASKFILE_BINARY run -- containers core build
```

Build specific modules:

```shell
TASKFILE_BINARY="./taskw"

$TASKFILE_BINARY run -- containers modules valkey-json build
```

Build valkey runtime including the modules:

```shell
TASKFILE_BINARY="./taskw"

$TASKFILE_BINARY run -- containers runtime build --modules valkey-json,valkey-search,valkey-bloom
```

Run built container using `podman`:

```shell
#!/bin/bash

CONTAINER="valkey9.0.1"
NETWORK="tumbleweed"
NETWORK_ALIAS="valkey9.0.1"
CONTAINER_UID=999
CONTAINER_GID=999
HOST_PORT=6379
VOLUME="valkey"
IMAGE="localhost/valkey:9.0.1"

podman volume exists $VOLUME || podman volume create $VOLUME

podman unshare chown -R $CONTAINER_UID:$CONTAINER_GID $(podman volume inspect $VOLUME --format '{{.Mountpoint}}')

podman run -d \
        --name $CONTAINER \
        --network $NETWORK \
        --network-alias $NETWORK_ALIAS \
        --user $CONTAINER_UID:$CONTAINER_GID \
        -p $HOST_PORT:6379 \
        -v $VOLUME:/var/lib/valkey/data \
        $IMAGE
```

## Application Container Image Features

### Modules

Valkey supports a dynamic module system that extends its core capabilities. This CLI tool compiles these modules from
source and integrates them into the runtime image.

#### JSON Document Store

<table> <thead> <th>Module</th> <th>Version</th> <th>Description</th> </thead> <tbody> <tr> <td><a href="https://github.com/valkey-io/valkey-json">valkey-json</a></td> <td>1.0.2</td> <td> <p>Adds native JSON support.</p> <p>Provides <code>JSON.SET</code>, <code>JSON.GET</code>, and standard <a href="https://goessner.net/articles/JsonPath/">JSONPath</a> syntax for deep access/modification.</p> </td> </tr> </tbody> </table>

#### Search & Vectors

<table> <thead> <th>Module</th> <th>Version</th> <th>Description</th> </thead> <tbody> <tr> <td><a href="https://github.com/valkey-io/valkey-search">valkey-search</a></td> <td>1.1.0</td> <td> <p>Secondary indexing, full-text search, and vector similarity search.</p> <p>Supports <strong>HNSW</strong> and <strong>Flat</strong> vector indexing for AI/LLM workloads.</p> <p>Automatically indexes data stored via <code>valkey-json</code>.</p> </td> </tr> </tbody> </table>

#### Probabilistic Data Structures

<table> <thead> <th>Module</th> <th>Version</th> <th>Description</th> </thead> <tbody> <tr> <td><a href="https://github.com/valkey-io/valkey-bloom">valkey-bloom</a></td> <td>1.0.0</td> <td> <p>High-performance probabilistic data structures.</p> <p><strong>Bloom Filter:</strong> High-speed set membership checks with zero false negatives.</p> <p><strong>Cuckoo Filter:</strong> Similar to Bloom but supports deletion.</p> <p><strong>Count-Min Sketch:</strong> Memory-efficient frequency counting.</p> </td> </tr> </tbody> </table>

### Ports

<table> <thead> <th>Port</th> <th>Purpose</th> </thead> <tbody> <tr> <td><code>6379</code></td> <td><strong>Default Valkey Port.</strong> Map this to your host using <code>-p 6379:6379</code>.</td> </tr> </tbody> </table>

### Volumes

<table> <thead> <th>Path</th> <th>Purpose</th> </thead> <tbody> <tr> <td><code>/var/lib/valkey/data</code></td> <td><strong>Data Directory.</strong> Stores the persistence files (<code>dump.rdb</code> and <code>appendonly.aof</code>). <strong>Note:</strong> Ensure you mount a volume here to prevent data loss on restart.</td> </tr> </tbody> </table>


