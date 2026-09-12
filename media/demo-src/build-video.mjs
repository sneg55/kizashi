import { execFileSync, spawnSync } from 'child_process'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const scenes = JSON.parse(fs.readFileSync(path.join(__dirname, 'scenes.json'), 'utf8'))
const CARDS = path.join(__dirname, 'out', 'cards')
const AUDIO = path.join(__dirname, 'out', 'audio')
const CAPS = path.join(__dirname, 'testreel-output')
const OUT = path.join(__dirname, 'out', 'demo.mp4')
const MIX = path.join(__dirname, 'out', 'mix.wav')

const W = 1920, H = 1080, FPS = 30, TAIL = 0.4, TARGET = 298, BG = '0xf9f9fb'
const LOUDNESS = -16, TRUE_PEAK = -1.5

const probe = (f) =>
  parseFloat(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nk=1:nw=1', f], { encoding: 'utf8' }).trim())

const latestCapture = (name) => {
  const files = fs.readdirSync(CAPS).filter((f) => f.startsWith(`${name}-`) && f.endsWith('.mp4'))
  if (!files.length) throw new Error(`no capture for "${name}" in testreel-output/`)
  files.sort()
  return path.join(CAPS, files[files.length - 1])
}

let sumDa = 0
for (const s of scenes) {
  s._audio = path.join(AUDIO, `${s.id}.wav`)
  if (!fs.existsSync(s._audio)) throw new Error(`missing narration for ${s.id}; run tts.mjs first`)
  s._da = probe(s._audio)
  sumDa += s._da
}
const factor = Math.max(1, sumDa / (TARGET - scenes.length * TAIL))
for (const s of scenes) s._len = s._da / factor + TAIL
const total = scenes.reduce((a, s) => a + s._len, 0)
console.log(`narration ${sumDa.toFixed(1)}s -> speed x${factor.toFixed(3)} -> final ~${total.toFixed(1)}s`)

const inputs = []
const filters = []
const concatLabels = []
let idx = 0
scenes.forEach((s, i) => {
  const L = s._len.toFixed(3)
  let vIdx
  if (s.kind === 'ui') {
    const cap = latestCapture(s.capture)
    const U = probe(cap)
    const hold = Math.max(0, s._len - U).toFixed(3)
    console.log(`  ${s.id}: capture ${U.toFixed(1)}s, scene ${s._len.toFixed(1)}s, freeze ${hold}s`)
    inputs.push('-i', cap)
    vIdx = idx++
    filters.push(
      `[${vIdx}:v]scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:-1:-1:color=${BG},fps=${FPS},setsar=1,tpad=stop_mode=clone:stop_duration=${hold},format=yuv420p,trim=0:${L},setpts=PTS-STARTPTS[v${i}]`
    )
  } else {
    inputs.push('-loop', '1', '-t', L, '-i', path.join(CARDS, `${s.id}.png`))
    vIdx = idx++
    filters.push(
      `[${vIdx}:v]scale=${W}:${H},fps=${FPS},setsar=1,format=yuv420p,trim=0:${L},setpts=PTS-STARTPTS[v${i}]`
    )
  }
  inputs.push('-i', s._audio)
  const aIdx = idx++
  const stretch = factor > 1.001 ? `atempo=${factor.toFixed(4)},` : ''
  filters.push(
    `[${aIdx}:a]${stretch}aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:${L},asetpts=N/SR/TB[a${i}]`
  )
  concatLabels.push(`[v${i}][a${i}]`)
})
filters.push(`${concatLabels.join('')}concat=n=${scenes.length}:v=1:a=1[v][araw]`)

const audioOnly = filters.filter((f) => !f.includes(':v]') && !f.startsWith(concatLabels[0]))
const audioLabels = scenes.map((_, i) => `[a${i}]`).join('')
const measureArgs = [
  '-y', '-loglevel', 'error',
  ...inputs,
  '-filter_complex', `${audioOnly.join(';')};${audioLabels}concat=n=${scenes.length}:v=0:a=1[am]`,
  '-map', '[am]', '-c:a', 'pcm_s16le', MIX,
]
console.log('measuring loudness...')
execFileSync('ffmpeg', measureArgs, { stdio: 'inherit' })
const report = spawnSync(
  'ffmpeg',
  ['-hide_banner', '-nostats', '-i', MIX, '-af', `loudnorm=I=${LOUDNESS}:TP=${TRUE_PEAK}:print_format=json`, '-f', 'null', '-'],
  { encoding: 'utf8' },
).stderr
const measured = JSON.parse(report.slice(report.lastIndexOf('{'), report.lastIndexOf('}') + 1))
fs.unlinkSync(MIX)
const gain = LOUDNESS - parseFloat(measured.input_i)
console.log(`integrated ${measured.input_i} LUFS, true peak ${measured.input_tp} dBTP -> static gain ${gain.toFixed(2)} dB`)
const limit = Math.pow(10, TRUE_PEAK / 20).toFixed(3)
filters.push(`[araw]volume=${gain.toFixed(2)}dB,alimiter=limit=${limit}:attack=5:release=50:level=false,aresample=48000[a]`)

const args = [
  '-y', '-loglevel', 'error',
  ...inputs,
  '-filter_complex', filters.join(';'),
  '-map', '[v]', '-map', '[a]',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
  '-c:a', 'aac', '-b:a', '192k',
  '-movflags', '+faststart',
  OUT,
]
console.log('encoding...')
execFileSync('ffmpeg', args, { stdio: 'inherit' })
console.log(`done -> ${path.relative(process.cwd(), OUT)} (${probe(OUT).toFixed(1)}s)`)
