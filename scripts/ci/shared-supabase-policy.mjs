#!/usr/bin/env node
// Template: shadow-devkit templates/ci/shared-supabase-policy.mjs → scripts/ci/shared-supabase-policy.mjs.
//
// Product repositories are linked to the shared production Supabase project, which only the Shadow Portal
// control plane may change (shadow-portal supabase/control-plane/product-repo-policy.md). This check fails when
// the lines a change adds contain a Supabase CLI command that may write to the hosted project, or the name of a
// credential that would let one run. It reads only added lines, so a cleanup that removes such a command passes.
// Run it from the hosted workflow and from the local equivalent gate (config/local-ci.json) alike.
//
// Flagged, the same set the agent hook (shadow-devkit agent-rules/hooks/command_guard.py) asks about:
//   db push, migration repair                        unless --local (v2 targets the linked project by default)
//   db reset, db query, migration up/down/squash     with --linked, --remote[=…], --db-url or --project-ref
//   config push, sso add/update/remove               always
//   SUPABASE_DB_PASSWORD, SUPABASE_ACCESS_TOKEN      anywhere
// Global flags may stand between command segments (`supabase --yes sso remove x`). A command ends at ; & | ( ) { }
// or a backtick; a redirection (`>log`, `2>&1`) skips its target and the command goes on. Within one hunk, an added
// line that ends in `\` is joined with the next added line, and in a YAML file a folded (`run: >-`) or plain scalar
// that goes on over more-indented added lines is also read as one line, so a command split over lines is read
// whole. A quoted string that contains a space, and a trailing `# comment`, are also read as commands of their own
// (package.json scripts, `bash -c '…'`); a comment's words are never arguments of the command before it. A segment whose subcommand is only known at run time
// ("$SUB") is not flagged. Prose that names a command, for example in Markdown, is flagged as well: reword it, or
// pass the file to --exclude.
//
// Usage: node scripts/ci/shared-supabase-policy.mjs [--base <rev>] [--head <rev>] [--exclude <pathspec>]...
//   --head defaults to HEAD; --base to the merge base of --head and origin/main. This file and package-lock.json
//   are always excluded. Output names file:line and the rule only, never the line, which may hold a secret.
// Exit status: 0 passed, 1 forbidden lines found, 2 usage or git error.
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SELF = 'scripts/ci/shared-supabase-policy.mjs';
const ALWAYS_EXCLUDED = [SELF, 'package-lock.json'];
const CREDENTIAL_RE = /SUPABASE_DB_PASSWORD|SUPABASE_ACCESS_TOKEN/;
// Flags whose value is the next word (Supabase CLI 3.0.0 --help, 2026-11-06).
const VALUED = new Set(['--workdir', '--profile', '--network-id', '--dns-resolver', '--output', '-o', '--output-format',
  '--log-level', '--agent', '--completions', '--project-ref', '--db-url', '--password', '-p']);
const SUBCOMMANDS = new Map([
  ['db', new Set(['advisors', 'branch', 'diff', 'dump', 'lint', 'pull', 'push', 'query', 'reset', 'start', 'test'])],
  ['migration', new Set(['down', 'fetch', 'list', 'new', 'repair', 'squash', 'up'])],
  ['config', new Set(['push'])],
  ['sso', new Set(['add', 'info', 'list', 'remove', 'show', 'update'])],
]);
const HOSTED = new Set(['config push', 'sso add', 'sso update', 'sso remove']);
const LINKED_DEFAULT = new Set(['db push', 'migration repair']);
const REMOTE_FLAGGED = new Set(['db reset', 'db query', 'migration up', 'migration down', 'migration squash']);
const REMOTE_RE = /^--(linked|remote|db-url|project-ref)(=.*)?$/;
const LOCAL = new Set(['--local', '--local=true', '--local=1']);
const ALIASES = new Map([['migrations', 'migration']]); // `supabase --help`: "migration, migrations"
const SEPARATORS = new Set([';', '&', '|', '(', ')', '{', '}', '`']);
const MAX_NESTING = 4;

/** Words of each command in a line, and the texts that may hold a command of their own: quoted strings with a space
 * and a trailing `#` comment, and a redirection target. A comment's words are not arguments of the command before it,
 * and a redirection (`>log`, `2>&1`, `>$(date +%F).log`) does not end the command: the whole target is skipped and
 * the command goes on. */
export function lex(text) {
  const segments = [[]];
  const nested = [];
  let word = null;
  const end = () => {
    if (word !== null) segments.at(-1).push(word);
    word = null;
  };
  for (let i = 0; i < text.length;) {
    const char = text[i];
    if (char === '#' && word === null) {
      nested.push(text.slice(i).replace(/^#+/, ''));
      break;
    }
    if (char === '<' || char === '>' || (char === '&' && text[i + 1] === '>')) {
      if (word !== null && /^\d+$/.test(word)) word = null; // the file descriptor in 2>
      end();
      while (i < text.length && '<>&'.includes(text[i])) i += 1;
      if (text[i - 1] === '>' && text[i] === '|') i += 1; // >|
      if (text[i] === '(') continue; // <(…) and >(…) are process substitutions, read as commands
      const target = redirectTarget(text, i);
      nested.push(target.text); // a command substitution inside the target still runs
      i = target.end;
      continue;
    }
    if (char === '"' || char === "'") {
      let content = '';
      let j = i + 1;
      while (j < text.length && text[j] !== char) {
        if (char === '"' && text[j] === '\\' && j + 1 < text.length) {
          content += text[j + 1];
          j += 2;
        } else {
          content += text[j];
          j += 1;
        }
      }
      if (/\s/.test(content)) nested.push(content);
      word = (word ?? '') + content;
      i = j + 1; // an unclosed quote runs to the end of the line
    } else if (char === '\\' && i + 1 < text.length) {
      word = (word ?? '') + text[i + 1];
      i += 2;
    } else if (/\s/.test(char)) {
      end();
      i += 1;
    } else if (SEPARATORS.has(char)) {
      end();
      if (segments.at(-1).length) segments.push([]);
      i += 1;
    } else {
      word = (word ?? '') + char;
      i += 1;
    }
  }
  end();
  return { segments: segments.filter((words) => words.length), nested };
}

/** The redirection target starting at or after text[i] (after blanks): one shell word, in which quotes, `$(…)`
 * and backticks do not end it. Returns its text and the index after it. */
function redirectTarget(text, i) {
  let k = i;
  while (k < text.length && /\s/.test(text[k])) k += 1;
  const start = k;
  if ((text[k] === '<' || text[k] === '>') && text[k + 1] === '(') k += 1; // > >(tee log): the target is <(…)/>(…)
  let depth = 0;
  let backtick = false;
  while (k < text.length) {
    const char = text[k];
    if (char === '\\') {
      k += 2;
    } else if ((char === '"' || char === "'") && !backtick) {
      const close = text.indexOf(char, k + 1);
      k = close < 0 ? text.length : close + 1;
    } else if (char === '`') {
      backtick = !backtick;
      k += 1;
    } else if (char === '(') {
      depth += 1;
      k += 1;
    } else if (char === ')' && depth > 0) {
      depth -= 1;
      k += 1;
    } else if (depth === 0 && !backtick && (/\s/.test(char) || ';&|<>()'.includes(char))) {
      break;
    } else {
      k += 1;
    }
  }
  return { text: text.slice(start, k).replace(/^[$<>]?\(|\)$/g, ' ').replace(/`/g, ' '), end: Math.min(k, text.length) };
}

function isSupabase(word) {
  const name = word.split('/').at(-1);
  return (name.startsWith('@') ? name : name.split('@')[0]) === 'supabase'; // npx supabase@3.0.0
}

/** The hosted write `supabase <args…>` performs, as "group action", or null. */
export function hostedWrite(args) {
  if (args.some((arg) => ['-h', '--help', '-v', '--version'].includes(arg))) return null;
  const positional = [];
  for (let k = 0; k < args.length; k += 1) {
    if (VALUED.has(args[k])) k += 1;
    else if (!args[k].startsWith('-')) positional.push(args[k]);
  }
  const [first, ...rest] = positional;
  const group = ALIASES.get(first) ?? first;
  const known = SUBCOMMANDS.get(group);
  const action = known && rest.find((word) => known.has(word));
  if (!action) return null;
  const pair = `${group} ${action}`;
  const remote = args.some((arg) => REMOTE_RE.test(arg));
  const local = args.some((arg) => LOCAL.has(arg));
  const hosted = HOSTED.has(pair) || (LINKED_DEFAULT.has(pair) && (remote || !local)) || (REMOTE_FLAGGED.has(pair) && remote);
  return hosted ? pair : null;
}

/** Rules a line breaks: "supabase <group> <action>" or "credential <NAME>". */
export function violations(text, depth = 0) {
  const found = new Set();
  const credential = CREDENTIAL_RE.exec(text);
  if (credential) found.add(`credential ${credential[0]}`);
  const { segments, nested } = lex(text);
  for (const words of segments) {
    words.forEach((word, index) => {
      const pair = isSupabase(word) ? hostedWrite(words.slice(index + 1)) : null;
      if (pair) found.add(`supabase ${pair}`);
    });
  }
  if (depth < MAX_NESTING) for (const inner of nested) for (const rule of violations(inner, depth + 1)) found.add(rule);
  return [...found];
}

// git quotes a path with a tab, newline, quote or backslash C-style (core.quotePath=false keeps other bytes as-is);
// the name is only shown in the report, so an escape JSON cannot read falls back to the quoted text.
function unquotePath(raw) {
  let value = raw;
  if (raw.startsWith('"')) {
    try {
      value = JSON.parse(raw);
    } catch {
      value = raw.slice(1, -1);
    }
  }
  return value.replace(/\t$/, '').replace(/^b\//, ''); // git ends a path that has a space with a tab
}

const YAML_FILE = /\.ya?ml$/;
const YAML_FOLDED = /^(\s*)(?:-\s+)?[^\s#][^#]*?:\s*>[-+0-9]*\s*(?:#.*)?$/; // key: >-
const YAML_PLAIN = /^(\s*)(?:-\s+)?[^\s#'"][^#]*?:\s+([^\s|>'"{[&*!#][^#]*)$/; // key: value
const YAML_ENTRY = /^\s*(?:-\s|[^\s#'"][^:#]*:(?:\s|$)|#)/; // a new key, list item or comment
const indent = (text) => /^\s*/.exec(text)[0].length;

/** YAML folds the lines of a folded scalar (`run: >-`) and of a plain scalar that goes on over more-indented lines
 * into one line, except where it keeps the line break: at a blank line, and in a folded scalar around a line indented
 * deeper than the first. Each such run of added lines is also returned as the lines YAML makes of it, so a command
 * split this way is read whole, and two commands YAML keeps apart stay apart. */
export function yamlFolds(entries) {
  const folds = [];
  for (let k = 0; k < entries.length; k += 1) {
    const head = entries[k];
    if (!YAML_FILE.test(head.file ?? '')) continue;
    const folded = YAML_FOLDED.exec(head.text);
    const plain = folded ? null : YAML_PLAIN.exec(head.text);
    if (!folded && !plain) continue;
    const body = [];
    let j = k + 1;
    while (j < entries.length && entries[j].file === head.file && entries[j].line === entries[j - 1].line + 1
      && (entries[j].text.trim() === '' || indent(entries[j].text) > indent(head.text))
      && !(plain && YAML_ENTRY.test(entries[j].text))) {
      body.push(entries[j]);
      j += 1;
    }
    if (!body.length) continue;
    const groups = [];
    let group = plain ? { line: head.line, parts: [plain[2].trim()] } : null;
    const close = () => {
      if (group?.parts.length) groups.push(group);
      group = null;
    };
    const base = indent(body.find((entry) => entry.text.trim() !== '')?.text ?? '');
    for (const entry of body) {
      const text = entry.text.trim();
      if (text === '') {
        close();
      } else if (folded && indent(entry.text) > base) {
        close();
        groups.push({ line: entry.line, parts: [text] });
      } else {
        group ??= { line: entry.line, parts: [] };
        group.parts.push(text);
      }
    }
    close();
    for (const { line, parts } of groups) folds.push({ file: head.file, line, text: parts.join(' ') });
    k = j - 1;
  }
  return folds;
}

/** Added lines of a unified diff as { file, line, text }, with `\` continuations inside one hunk joined. */
export function addedLines(diff) {
  const out = [];
  let file = null;
  let inHunk = false;
  let next = 0;
  let pending = null;
  const flush = () => {
    if (pending) out.push(pending);
    pending = null;
  };
  for (const line of diff.split('\n')) {
    if (line.startsWith('diff --git ')) {
      flush();
      inHunk = false;
      file = null;
    } else if (line.startsWith('@@')) {
      flush();
      inHunk = true;
      next = Number(/\+(\d+)/.exec(line)?.[1] ?? 0);
    } else if (!inHunk) {
      if (line.startsWith('+++ ')) file = unquotePath(line.slice(4));
    } else if (line.startsWith('+')) {
      const text = line.slice(1);
      if (pending) pending.text = pending.text.slice(0, -1) + text;
      else pending = { file, line: next, text };
      next += 1;
      if (!pending.text.endsWith('\\')) flush();
    } else {
      flush();
      if (line.startsWith(' ')) next += 1;
    }
  }
  flush();
  return out;
}

function git(args) {
  const result = spawnSync('git', args, { encoding: 'utf8', maxBuffer: 512 * 1024 * 1024 });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`git ${args.join(' ')}: ${result.stderr.trim()}`);
  return result.stdout;
}

export function main(argv = process.argv.slice(2)) {
  let base;
  let head = 'HEAD';
  const excludes = [];
  for (let i = 0; i < argv.length; i += 1) {
    const value = argv[i + 1];
    if (!['--base', '--head', '--exclude'].includes(argv[i]) || value === undefined || value.startsWith('--')) {
      console.error('usage: shared-supabase-policy.mjs [--base <rev>] [--head <rev>] [--exclude <pathspec>]...');
      return 2;
    }
    if (argv[i] === '--base') base = value;
    else if (argv[i] === '--head') head = value;
    else excludes.push(value);
    i += 1;
  }
  try {
    if (base !== undefined && /^0+$/.test(base)) throw new Error('no comparable base commit; the policy cannot prove the boundary');
    base ??= git(['merge-base', head, 'origin/main']).trim();
    const pathspecs = [...ALWAYS_EXCLUDED, ...excludes].map((spec) => `:(exclude)${spec}`);
    const diff = git(['-c', 'core.quotePath=false', 'diff', '--unified=0', '--no-color', '--no-ext-diff', '--no-textconv', base, head, '--', '.', ...pathspecs]);
    const lines = addedLines(diff);
    const reported = new Set();
    const hits = [...lines, ...yamlFolds(lines)]
      .flatMap((entry) => violations(entry.text).map((rule) => ({ ...entry, rule })))
      .filter((hit) => !reported.has(`${hit.file}:${hit.line}: ${hit.rule}`) && reported.add(`${hit.file}:${hit.line}: ${hit.rule}`));
    if (hits.length) {
      for (const hit of hits) console.error(`${hit.file}:${hit.line}: ${hit.rule}`);
      console.error('shared-supabase-policy: product repositories may not add commands that write to the shared hosted '
        + 'Supabase project (migrations, shared Auth settings, SSO providers) or its credentials. See shadow-portal '
        + 'supabase/control-plane/product-repo-policy.md.');
      return 1;
    }
    console.log(`shared-supabase-policy: passed (${lines.length} added lines, ${base.slice(0, 12)}..${head})`);
    return 0;
  } catch (error) {
    console.error(`shared-supabase-policy: ${error.message}`);
    return 2;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exitCode = main();
