#!/bin/bash

diff() {
    git diff --word-diff=color --diff-filter=M ../linux-6.6.47 .
}

# 检查哪些文件应该 git ignore 但是没有 ignore 的
new_files() {
    make -C ../linux-6.6.47 mrproper
    find . -type f | grep -v '^\./\.git' |
        grep -E -v '^\./build\.sh|^\./README\.md|^\./debug\.mk' |
    while read -r line; do
        [[ -f ../linux-6.6.47/${line} ]] && continue
        git check-ignore "${line}" -q && continue
        echo "${line}" 
    done
}

cp_makefile() {
    pushd ../linux-6.6.47
    make mrproper

    for makefile in Kbuild 'Makefile*'; do
        find . -type f  -name "${makefile}" | 
        \
    while read -r line; do
        [[ -f ../ut6/${line} ]] && continue
        mkdir -p $(dirname ../ut6/${line})
        echo cp ${line} ../ut6/${line}
        cp ${line} ../ut6/${line}
    done

    done

    popd
}

[[ -n "${*}" ]] && "${@}"
