#!/bin/bash

diff() {
    git diff --diff-filter=M ../linux-6.6.47 .
}

[[ -n "${*}" ]] && "${@}"
