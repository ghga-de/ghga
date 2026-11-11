#!/usr/bin/env bash
# `just demo-load [profile] [reclaim]`: copy the profile's built images from the docker
# store into the kind node.
#
# Safe to re-run, which is why `up` can depend on it unconditionally — but not free: kind's
# "already present" check compares the docker image ID against the node's, and with
# docker's containerd image store those never match, so every image is re-copied on every
# run (~40 s for the full per-member set, a couple of seconds for the mono profile).
# Measured, not assumed — do not "optimise" this by skipping the load.
#
# Loads the set the requested profile actually deploys, NOT everything in the docker store:
# a store holding both profiles would otherwise load 24 images to run the 2 the mono profile
# needs, throwing away most of what mono buys.
#
# reclaim=true (CI) drops each docker copy once it is loaded: `kind load` copies into the
# node's containerd, so keeping both doubles the footprint for no gain on a one-shot runner.
# Locally the default keeps both — a later reload then costs no rebuild at all.
#
# Env: IMAGE_REGISTRY, the registry root the images are tagged under.
set -euo pipefail

profile=${1:-}
reclaim=${2:-false}

# Assignments rather than process substitution, so a failing listing fails the script.
case "$profile" in
    "") names=$(python3 scripts/image_members.py --field package) ;;
    # in the mono profile the Python members are all inside the one image; the members
    # shipping their own Dockerfile still need theirs
    mono) names="$(python3 scripts/image_members.py --kind frontend --field package) platform" ;;
    *) echo "error: unknown profile '$profile' (expected 'mono', or nothing)" >&2; exit 1 ;;
esac

# what the node already has, so a reclaimed docker store is not mistaken for "never
# built": reclaim=true deletes each docker copy after loading it, and `up`/`testbed-up`
# re-enter this recipe as a dependency afterwards
node_images=$(docker exec ghga-control-plane crictl images 2> /dev/null | awk 'NR>1 {print $1":"$2}' || true)
loaded=0
already=0
for name in $names; do
    ref="$IMAGE_REGISTRY/$name:local"
    if ! docker image inspect "$ref" > /dev/null 2>&1; then
        if printf '%s\n' "$node_images" | grep -Fx "$ref" > /dev/null; then
            already=$((already + 1))
        fi
        continue
    fi
    kind load docker-image --name ghga "$ref"
    loaded=$((loaded + 1))
    if [ "$reclaim" = "true" ]; then
        docker image rm "$ref" > /dev/null
        docker builder prune -f --keep-storage 4GB > /dev/null
    fi
done
if [ $((loaded + already)) -eq 0 ]; then
    echo "error: no ghga images in the docker store or on the node — run \`just demo-images\` (or \`just demo-images-mono\`) first" >&2
    exit 1
fi
echo "loaded $loaded image(s) into the kind node ($already already there)"
