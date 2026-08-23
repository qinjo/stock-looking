// 构建后把 dist 产物复制到 stocklook/static，由 Flask 直接托管
import { cpSync, mkdirSync, rmSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const dist = join(here, '..', 'dist')
const target = join(here, '..', '..', 'stocklook', 'static')

rmSync(target, { recursive: true, force: true })
mkdirSync(target, { recursive: true })
cpSync(dist, target, { recursive: true })
console.log(`已复制前端产物 → ${target}`)