#!node

const path = require('path')
const args = process.argv
const fs = require('fs')

const base = path.basename(args[2])
const cmd = "." + (
    base.endsWith(".S") || base.endsWith(".c") || base.endsWith(".s") ?
        base.replace(/\..$/, ".o") :
        base
) + ".cmd"

console.log(
    fs.readFileSync(path.join(path.dirname(args[2]), cmd), 'utf8').split('\n')[0].split(':=')
)

