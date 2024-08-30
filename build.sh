#!/bin/bash

diff() {
    git diff --word-diff=color --diff-filter=M ../linux-6.6.47 .
}

[[ -n "${*}" ]] && "${@}"
