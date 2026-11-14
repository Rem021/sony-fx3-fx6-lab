#!/usr/bin/env node
import { DatabaseSync } from "node:sqlite";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const REPO_ID = "e52bdbc7-1cf3-4bc8-bdd4-f37b01044ebd";
const REPO_PATH = resolve(import.meta.dirname, "..");
const MAC_PATH = resolve(REPO_PATH, "../..");
const { rpcBatch } = await import(pathToFileURL(join(MAC_PATH, "outputs/orca-naming-guard/adapter.mjs")).href);
const ACTIVE_SESSION_ID = "antigravity_7a23fc7b_dfcf_4785_bc33_b678bbc0e0f0";
const LEGACY_WORKSPACE_ID = `3a0322f4-f7ac-4feb-bd18-5c4fddb66fae::${MAC_PATH}::workspace:033512d4-46a1-40b1-bb3a-3eb39c298577`;

const WORKSPACES = {
  cat1: {
    id: `${REPO_ID}::${REPO_PATH}`,
    name: "FX3｜FX6 系统移植与跨机型总览",
    dir: "01-fx6-system-porting",
    descZh: "FX6 v5.00 (ILME-FX6V) 跨机型移植至 FX3 模拟器、分区/NOR 兼容矩阵、CapID/GRM 前沿与启动门禁审计",
    descEn: "FX6 v5.00 (ILME-FX6V) System Porting to FX3 Emulator, Partition/NOR Compatibility Matrix, CapID/GRM Frontier & Boot Gate Audits"
  },
  cat2: {
    id: `${REPO_ID}::${REPO_PATH}::workspace:4055ad3d-0701-4f8f-954a-509020e82fde`,
    name: "FX3｜FX5 固件解包与电影菜单色彩移植",
    dir: "02-fx5-unpack-and-cinema-color",
    descZh: "FX5 固件解包、VENICE 色彩科学管线与 FX3 电影菜单（Cine EI / 色彩控制）移植研究",
    descEn: "FX5 Firmware Unpacking, VENICE Color Science Chain & FX3 Cinema Menu / Color Control Porting"
  },
  cat3: {
    id: `${REPO_ID}::${REPO_PATH}::workspace:b243cace-076f-4609-864a-920dbda55931`,
    name: "FX3｜固件逆向与 H.265 编码研究",
    dir: "03-fx3-firmware-re-and-h265",
    descZh: "Sony FX3 / ZV-E1 固件解包逆向、Bionz XR 双核 IPC、H.265/HEVC 编码模式与 iCrypt 符号审计",
    descEn: "Sony FX3 / ZV-E1 Firmware Reverse Engineering, Bionz XR Dual-Core IPC, H.265/HEVC Encoding & iCrypt Symbol Audits"
  },
  cat4: {
    id: `${REPO_ID}::${REPO_PATH}::workspace:2a92721a-f206-4472-82a5-edf30db5be8c`,
    name: "FX3｜虚拟机主屏菜单与 GPE 渲染修复",
    dir: "04-fx3-vm-menu-and-gpe",
    descZh: "FX3 QEMU 模拟器主屏开机、GPE 2D 渲染引擎、ldec LZ77 图标解码、VDF/ADF/OSD/SKD 协议与 r21–r43 八步菜单验收",
    descEn: "FX3 QEMU Emulator Home Screen Bring-up, GPE 2D Engine, ldec LZ77 Decoder, VDF/ADF/OSD/SKD Protocols & r21–r43 8-Step Menu Verification"
  },
  cat5: {
    id: `${REPO_ID}::${REPO_PATH}::workspace:312a194a-d58d-4e37-afbb-4cdafd74fbea`,
    name: "FX3｜真机刷机安全与变砖恢复研究",
    dir: "05-fx3-flash-safety-and-recovery",
    descZh: "FX3 真机刷机门禁安全、变砖救援分析、文件级安装与恢复链路审计",
    descEn: "FX3 Hardware Flashing Safety Guards, Brick Recovery Analysis & File-Level Installation / Recovery Audits"
  }
};

const TITLE_OVERRIDES = {
  "antigravity_0399b63f_b78a_42fa_a296_7c7bdd04179f": "FX3｜FX6 系统移植进度与开源总控",
  "bd85f19c-07bc-4aed-8701-28d1870ee530": "FX6｜系统移植到 FX3 模拟器与 CapID 门禁",
  "110628ec-2eab-4f2a-a73e-63003ae78468": "FX3｜项目总览与模拟器复现审计",
  "a635de3d-4f25-4dc1-821a-179d3ce27f55": "FX6｜固件解包与跨机型兼容矩阵",
  "2029c357-e101-47fb-b97f-4c314b03a269": "FX6｜根镜像构造与早期引导冒烟测试",
  "7a4acb16-6962-439d-8279-fa54492a20d4": "FX6｜启动门禁与硬件缺口深度审计",
  "codex_34f9e042_5600_486c_8a70_38ee129c1e41": "FX5｜固件解包与 FX3 电影菜单移植",
  "codex_f85e2172_232f_4fa1_bd18_a437425e0300": "FX5｜固件解包与 FX3 菜单移植 A",
  "codex_3feda637_a4b5_4e62_926d_f4b5cad2155d": "FX5｜固件解包与 FX3 菜单移植 B",
  "b7c509a3-1e1c-4f9c-a89d-2356664f3e36": "FX3｜电影菜单与色彩控制设计",
  "claude_51766bb7_ee7b_4f20_a5de_5fa0e6360865": "FX3｜固件与编码研究",
  "codex_efeca0de_a058_4a45_b27a_49c0ce6a89b6": "FX3｜固件逆向与 H.265 研究",
  "antigravity_93b29963_4e83_434d_b4e9_c2193c6a8ebd": "FX3｜索尼 FX3 固件逆向研究 A",
  "antigravity_a60766bf_8586_4d3d_af62_3361630fd51a": "FX3｜索尼 FX3 固件逆向研究 B",
  "09e6b13c-b70a-4c72-ac63-d1c7e5f0d3ae": "FX3｜iCrypt 缺失库与未解析符号审计",
  "codex_e7af8c22_4597_4793_b846_dfcc4082aee1": "FX3｜Sony FX3 变砖与固件恢复",
  "99504134-50c1-4763-8804-cf304fae1641": "FX3｜文件级安装与恢复审计",
  "claude_9e4c5454_f5cd_4f55_aeef_607246611258": "FX3｜虚拟机菜单修复续接",
  "codex_24be8e23_8e3e_4d26_904d_687c069d1839": "FX3｜虚拟机菜单修复主线 A",
  "codex_d07cbfc0_127b_4016_a71b_fb7af87caf07": "FX3｜虚拟机菜单修复主线 B",
  "4b466c26-c07a-4d1e-bd2f-94fe86991fe1": "FX3｜VDF 服务与公共上下文预审",
  "cfee9d71-c386-47eb-bf6d-659c9ad25c77": "FX3｜宿主重复像素编码缓存优化",
  "98f50f73-d98d-42ba-b7ec-c20148c39d11": "FX3｜宿主异常记录修复与离线测试",
  "85213b32-f08f-4e7d-8cd3-df4317b4d8fd": "FX3｜画面停更离线定位审计",
  "7f0b23bd-24a3-46e5-9f3a-08e73dc267a7": "FX3｜MPR 返回值与结构体布局比对",
  "4c2e0d3c-cb34-4eb3-99ac-2842298a4684": "FX3｜绘制等待与 MENU 处理诊断 v25"
};

function categorizeSession(sid, title) {
  if ([
    "antigravity_0399b63f_b78a_42fa_a296_7c7bdd04179f",
    "bd85f19c-07bc-4aed-8701-28d1870ee530",
    "110628ec-2eab-4f2a-a73e-63003ae78468",
    "a635de3d-4f25-4dc1-821a-179d3ce27f55",
    "2029c357-e101-47fb-b97f-4c314b03a269",
    "7a4acb16-6962-439d-8279-fa54492a20d4"
  ].includes(sid)) return "cat1";
  if ([
    "codex_34f9e042_5600_486c_8a70_38ee129c1e41",
    "codex_f85e2172_232f_4fa1_bd18_a437425e0300",
    "codex_3feda637_a4b5_4e62_926d_f4b5cad2155d",
    "b7c509a3-1e1c-4f9c-a89d-2356664f3e36"
  ].includes(sid)) return "cat2";
  if ([
    "claude_51766bb7_ee7b_4f20_a5de_5fa0e6360865",
    "codex_efeca0de_a058_4a45_b27a_49c0ce6a89b6",
    "antigravity_93b29963_4e83_434d_b4e9_c2193c6a8ebd",
    "antigravity_a60766bf_8586_4d3d_af62_3361630fd51a",
    "09e6b13c-b70a-4c72-ac63-d1c7e5f0d3ae"
  ].includes(sid)) return "cat3";
  if ([
    "codex_e7af8c22_4597_4793_b846_dfcc4082aee1",
    "99504134-50c1-4763-8804-cf304fae1641"
  ].includes(sid)) return "cat5";
  return "cat4";
}

function redactSecrets(text) {
  if (!text) return "";
  return String(text)
    .replace(/gh[pousr]_[A-Za-z0-9_]{20,}/g, "[REDACTED_GITHUB_TOKEN]")
    .replace(/github_pat_[A-Za-z0-9_]{20,}/g, "[REDACTED_GITHUB_PAT]")
    .replace(/sk-[A-Za-z0-9_-]{20,}/g, "[REDACTED_API_KEY]")
    .replace(/AIza[0-9A-Za-z_-]{35}/g, "[REDACTED_GOOGLE_KEY]")
    .replace(/"authToken"\s*:\s*"[^"]+"/g, '"authToken":"[REDACTED]"');
}

const dbPath = "/Users/kafu/Library/Application Support/orca/agent-session-journal.db";
const db = new DatabaseSync(dbPath);

const TargetWids = new Set([
  LEGACY_WORKSPACE_ID,
  `3a0322f4-f7ac-4feb-bd18-5c4fddb66fae::${MAC_PATH}`,
  "3a0322f4-f7ac-4feb-bd18-5c4fddb66fae::/Volumes/KAFU2T/AI/Projects/Mac::workspace:033512d4-46a1-40b1-bb3a-3eb39c298577",
  "3a0322f4-f7ac-4feb-bd18-5c4fddb66fae::/Volumes/KAFU2T/AI/Projects/Mac",
  ...Object.values(WORKSPACES).map(w => w.id),
  ...Object.values(WORKSPACES).map(w => w.id.replace(REPO_PATH, "/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab"))
]);

const SKIP_SIDS = new Set([
  "codex_e11888aa_04c3_4387_82d6_f77213382b49",
  "codex_9d2b1086_4e4f_437e_b4ba_e9eccdc6fdc7",
  "codex_d582687f_6dda_4b6a_97d3_1489e120ec06",
  "antigravity_a98ab18a_463d_41bb_88f1_a30f12c72504"
]);

const rawRecords = db.prepare("SELECT session_id, record_json FROM agent_session_records").all();
const sessions = [];

for (const row of rawRecords) {
  const sid = row.session_id;
  if (SKIP_SIDS.has(sid)) continue;
  const r = JSON.parse(row.record_json);
  const wid = r.location?.workspaceId ?? "";
  const cname = r.conversationName ?? "";
  if (!TargetWids.has(wid)) continue;
  if (wid.endsWith("::/Volumes/KAFU2T/AI/Projects/Mac") && !/FX3|FX5|FX6|SONY|索尼/i.test(cname)) continue;
  const targetTitle = TITLE_OVERRIDES[sid] ?? cname;
  const catKey = categorizeSession(sid, targetTitle);
  sessions.push({
    sid,
    provider: r.provider,
    oldTitle: cname,
    title: targetTitle,
    oldWorkspaceId: wid,
    catKey,
    targetWorkspaceId: WORKSPACES[catKey].id,
    createdAt: r.createdAt ?? 0,
    updatedAt: r.updatedAt ?? 0,
    record: r
  });
}

sessions.sort((a, b) => b.updatedAt - a.updatedAt);
console.log(`Categorized ${sessions.length} FX3/FX5/FX6 sessions across 5 workspaces.`);

// 1. Rename sessions that need title normalization
const renameCalls = sessions
  .filter(s => s.oldTitle !== s.title)
  .map(s => ({
    method: "agentSession.rename",
    params: { sessionId: s.sid, name: s.title }
  }));

if (renameCalls.length > 0) {
  const res = await rpcBatch(renameCalls);
  console.log(`Renamed ${res.length} sessions to normalized FX3/FX5/FX6 titles.`);
}

// 2. Bind sessions to their categorized Orca workspaces in agent-session-journal.db
const updateJournalStmt = db.prepare("UPDATE journal_sessions SET workspace_id = ? WHERE session_id = ?");
const updateRecordStmt = db.prepare("UPDATE agent_session_records SET record_json = ? WHERE session_id = ?");

let boundCount = 0;
db.exec("BEGIN IMMEDIATE");
try {
  for (const s of sessions) {
    if (s.sid === ACTIVE_SESSION_ID) continue;
    if (s.oldWorkspaceId !== s.targetWorkspaceId) {
      updateJournalStmt.run(s.targetWorkspaceId, s.sid);
      const updatedRecord = {
        ...s.record,
        conversationName: s.title,
        location: {
          ...(s.record.location ?? {}),
          workspaceId: s.targetWorkspaceId
        }
      };
      updateRecordStmt.run(JSON.stringify(updatedRecord), s.sid);
      boundCount++;
    }
  }
  const leftoverRows = db.prepare("SELECT session_id FROM journal_sessions WHERE workspace_id = ?").all(LEGACY_WORKSPACE_ID);
  for (const row of leftoverRows) {
    if (row.session_id === ACTIVE_SESSION_ID) continue;
    updateJournalStmt.run(WORKSPACES.cat1.id, row.session_id);
    const recRow = db.prepare("SELECT record_json FROM agent_session_records WHERE session_id = ?").get(row.session_id);
    if (recRow?.record_json) {
      const parsed = JSON.parse(recRow.record_json);
      parsed.location = { ...(parsed.location ?? {}), workspaceId: WORKSPACES.cat1.id };
      updateRecordStmt.run(JSON.stringify(parsed), row.session_id);
    }
    boundCount++;
  }
  db.exec("COMMIT");
} catch (err) {
  db.exec("ROLLBACK");
  throw err;
}
db.close();
console.log(`Bound ${boundCount} sessions to their categorized FX3/FX5/FX6 workspaces in agent-session-journal.db.`);

// 3. Export conversation markdown files into sony-fx3-fx6-lab/conversations/
const convRoot = join(REPO_PATH, "conversations");
mkdirSync(convRoot, { recursive: true });
for (const w of Object.values(WORKSPACES)) {
  mkdirSync(join(convRoot, w.dir), { recursive: true });
}

const byCat = { cat1: [], cat2: [], cat3: [], cat4: [], cat5: [] };
for (const s of sessions) byCat[s.catKey].push(s);

for (const s of sessions) {
  let items = [];
  try {
    const [h] = await rpcBatch([{
      method: "agentSession.history",
      params: { sessionId: s.sid, direction: "tail", limit: 200 }
    }]);
    items = h?.page?.items ?? [];
  } catch (e) {
    console.warn("History fetch warning for", s.sid, e.message);
  }
  const msgItems = items.filter(it => it.body?.kind === "message" && (it.body?.role === "user" || it.body?.role === "assistant"));
  const safeSlug = s.title.replace(/[\/\\:*?"<>|\s]+/g, "-").replace(/^-+|-+$/g, "");
  const fileName = `${safeSlug}-${s.sid.slice(0, 12)}.md`;
  s.archiveFile = `conversations/${WORKSPACES[s.catKey].dir}/${fileName}`;
  s.messageCount = msgItems.length;

  const lines = [
    `# ${s.title}`,
    "",
    `- **Session ID**: \`${s.sid}\``,
    `- **Agent Provider**: \`${s.provider}\``,
    `- **Orca Category Workspace**: \`${WORKSPACES[s.catKey].name}\``,
    `- **Orca Workspace ID**: \`${s.targetWorkspaceId}\``,
    `- **Created At**: \`${new Date(s.createdAt).toISOString()}\``,
    `- **Updated At**: \`${new Date(s.updatedAt).toISOString()}\``,
    `- **Captured Messages (User / Assistant)**: \`${msgItems.length}\``,
    "",
    "---",
    ""
  ];

  for (const m of msgItems) {
    const roleLabel = m.body.role === "user" ? "## 👤 User / Coordinator" : "## 🤖 Assistant";
    const textBlocks = (m.body.blocks ?? [])
      .filter(b => b.type === "text" && b.text)
      .map(b => redactSecrets(b.text.trim()))
      .filter(Boolean);
    if (textBlocks.length === 0) continue;
    lines.push(roleLabel);
    lines.push("");
    lines.push(textBlocks.join("\n\n"));
    lines.push("");
    lines.push("---");
    lines.push("");
  }

  writeFileSync(join(REPO_PATH, s.archiveFile), lines.join("\n"), "utf8");
}

const masterLines = [
  "# Sony FX3 / FX5 / FX6 Research Conversation Archives (Orca 专项研究对话全集)",
  "",
  "> **Auto-Synced to GitHub**: All 86 FX3, FX5, and FX6 system research conversations in Orca Project **`FX3｜FX5 & FX6 系统研究`** (`e52bdbc7-1cf3-4bc8-bdd4-f37b01044ebd`) are categorized across 5 thematic workspaces and automatically synced to this directory.",
  "",
  "## Category Overview (五大研究工作区归类总览)",
  "",
  "| # | Orca Workspace (`FX3｜...`) | Directory | Conversations | Focus Area |",
  "|---|---|---|---|---|"
];

let idx = 1;
for (const [catKey, w] of Object.entries(WORKSPACES)) {
  const list = byCat[catKey];
  masterLines.push(`| ${idx} | **${w.name}** | [\`${w.dir}/\`](./${w.dir}/README.md) | **${list.length}** | ${w.descZh}<br>*(${w.descEn})* |`);
  idx++;

  const catLines = [
    `# ${w.name}`,
    "",
    `> **中文说明**：${w.descZh}`,
    `> **English**: ${w.descEn}`,
    "",
    `- **Orca Workspace ID**: \`${w.id}\``,
    `- **Total Conversations**: **${list.length}**`,
    "",
    "| # | Title (对话主题) | Agent | Messages | Updated (UTC) | Archive File |",
    "|---|---|---|---|---|---|"
  ];
  list.forEach((s, i) => {
    const fbase = s.archiveFile.split("/").pop();
    catLines.push(`| ${i + 1} | **${s.title}** | \`${s.provider}\` | ${s.messageCount} | \`${new Date(s.updatedAt).toISOString().slice(0, 16)}Z\` | [\`${fbase}\`](./${fbase}) |`);
  });
  catLines.push("");
  writeFileSync(join(convRoot, w.dir, "README.md"), catLines.join("\n"), "utf8");
}

masterLines.push("");
for (const [catKey, w] of Object.entries(WORKSPACES)) {
  const list = byCat[catKey];
  masterLines.push(`## ${w.name} (${list.length})`);
  masterLines.push("");
  masterLines.push(`- **Description**: ${w.descZh} / *${w.descEn}*`);
  masterLines.push("");
  masterLines.push("| # | Conversation Title | Agent | Messages | Updated (UTC) | Archive Link |");
  masterLines.push("|---|---|---|---|---|---|");
  list.forEach((s, i) => {
    masterLines.push(`| ${i + 1} | **${s.title}** | \`${s.provider}\` | ${s.messageCount} | \`${new Date(s.updatedAt).toISOString().slice(0, 16)}Z\` | [View Archive](../${s.archiveFile}) |`);
  });
  masterLines.push("");
}

writeFileSync(join(convRoot, "README.md"), masterLines.join("\n"), "utf8");
console.log(`Exported all ${sessions.length} conversation markdown files and indexes.`);
