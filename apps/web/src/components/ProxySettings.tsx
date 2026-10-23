import {
  Alert, Badge, Button, Code, Group, Paper, PasswordInput, Stack, Switch, Text, TextInput, Title,
} from "@mantine/core";
import { IconAlertCircle, IconCheck } from "@tabler/icons-react";
import { useEffect, useState } from "react";

import { getProxies, parseProxy, saveProxy, testProxy, type ProxyInfo } from "../api/client";

const DEFAULT_CLASH = "http://127.0.0.1:7897";
const ROUTES = {
  direct: "项目 → 后端电脑的网络出口",
  proxy: "项目 → 填写的代理 → 目标网站",
  clash: "项目 → 本机 Clash → 填写的代理 → 目标网站",
};

function Facts({ info }: { info: ProxyInfo }) {
  return (
    <Group gap="xs">
      <Badge variant="light" color="gray" tt="none">{info.scheme}://{info.host}:{info.port}</Badge>
      <Badge variant="light" color="indigo" tt="none">账号目标地区 {info.region || "未指定"}</Badge>
      <Badge variant="light" color="gray" tt="none">SID {info.sid || "未指定"}</Badge>
    </Group>
  );
}

export function ProxySettings() {
  const [raw, setRaw] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [useClash, setUseClash] = useState(false);
  const [clashUrl, setClashUrl] = useState(DEFAULT_CLASH);
  const [saved, setSaved] = useState<ProxyInfo | null>(null);
  const [preview, setPreview] = useState<ProxyInfo | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [message, setMessage] = useState<{ color: "red" | "green"; text: string } | null>(null);
  const [busy, setBusy] = useState<"parse" | "save" | "test" | null>(null);

  function loadSettings(info: ProxyInfo) {
    setSaved(info);
    setEnabled(info.enabled);
    setUseClash(info.use_clash ?? false);
    setClashUrl(info.clash_proxy_url || DEFAULT_CLASH);
  }

  useEffect(() => {
    getProxies().then((all) => {
      loadSettings(all.checkout);
      setLoaded(true);
    }).catch(() => setMessage({ color: "red", text: "无法读取已保存的代理配置，请检查后端后刷新页面。" }));
  }, []);

  async function run(kind: "parse" | "save" | "test", action: () => Promise<void>) {
    setBusy(kind);
    setMessage(null);
    try {
      await action();
    } catch (err) {
      setMessage({ color: "red", text: err instanceof Error ? err.message : "操作失败" });
    } finally {
      setBusy(null);
    }
  }

  const configured = Boolean(saved?.host);
  const dirty = Boolean(raw) || enabled !== Boolean(saved?.enabled)
    || useClash !== Boolean(saved?.use_clash) || clashUrl !== (saved?.clash_proxy_url || DEFAULT_CLASH);
  const mode = !saved?.enabled ? "direct" : saved.use_clash ? "clash" : "proxy";
  const locked = !loaded || busy !== null;

  return (
    <Stack gap="lg" maw={720}>
      <div>
        <Title order={4}>出口代理</Title>
        <Text size="sm" c="dimmed">
          只有需要中转的代理才开启 Clash。账单国家和代理账号目标地区不代表实际网络出口，请通过测试连接查看出口 IP。
        </Text>
      </div>

      <Paper withBorder p="md" radius="md">
        <Stack gap="xs">
          <Group justify="space-between">
            <Text fw={600} size="sm">当前已保存配置</Text>
            <Badge color={saved?.enabled ? "green" : "gray"} variant="light">
              {!loaded ? "未读取" : configured ? (saved?.enabled ? "已启用" : "已停用") : "未配置"}
            </Badge>
          </Group>
          {configured && saved && <Facts info={saved} />}
          {loaded && <Text size="sm">{ROUTES[mode]}</Text>}
          {mode === "clash" && <Text size="sm" c="dimmed">Clash 入口：{saved?.clash_proxy_url}</Text>}
          {loaded && mode === "direct" && <Text size="sm" c="dimmed">
            未指定应用层代理，实际出口取决于后端电脑的网络；系统 VPN 或 TUN 仍可能影响路由。项目不提供默认美国代理。
          </Text>}
        </Stack>
      </Paper>

      <PasswordInput
        label="代理地址"
        description="新建或更换代理时填写；只修改开关时留空，将保留已保存的账号密码。支持 http://账号:密码@主机:端口、主机:端口:账号:密码、socks5://…。"
        placeholder="填写新的代理地址，或留空保留当前代理"
        value={raw}
        disabled={locked}
        onChange={(event) => {
          const next = event.currentTarget.value.trim();
          setRaw(next);
          setPreview(null);
          setMessage(null);
          if (next) {
            setUseClash(false);
            if (!raw) setEnabled(true);
          } else if (saved) {
            loadSettings(saved);
          }
        }}
      />
      <Group>
        <Button variant="light" loading={busy === "parse"} disabled={locked || !raw}
          onClick={() => void run("parse", async () => setPreview(await parseProxy(raw)))}>
          解析预览
        </Button>
      </Group>

      {preview && <Paper withBorder p="md" radius="md">
        <Stack gap="sm">
          <Text fw={600} size="sm">新代理解析结果</Text>
          <Facts info={preview} />
          {preview.has_username && (!preview.has_region_param || !preview.has_sid_param) && (
            <Alert color="yellow" icon={<IconAlertCircle size={18} />}>
              此账号未包含完整的地区 / SID 参数。创建订单时可能追加 <Code>-region-XX</Code> / <Code>-sid-随机值</Code>，请确认供应商支持此格式。
            </Alert>
          )}
        </Stack>
      </Paper>}

      <Switch label="启用代理" checked={enabled} disabled={locked || (!configured && !raw)}
        onChange={(event) => setEnabled(event.currentTarget.checked)} />
      <Switch label="通过本机 Clash 连接" checked={useClash} disabled={locked || !enabled}
        description="打开：先经过 Clash，再连接上方代理。关闭：直接连接上方代理。更换代理时默认关闭。"
        onChange={(event) => setUseClash(event.currentTarget.checked)} />
      {useClash && <TextInput label="Clash 地址" value={clashUrl} disabled={locked || !enabled}
        description="填写运行后端的电脑上的 HTTP / Mixed 入口。请先启动 Clash；连接失败不会自动改为直连。"
        placeholder={DEFAULT_CLASH} onChange={(event) => setClashUrl(event.currentTarget.value)} />}

      <Group>
        <Button loading={busy === "save"}
          disabled={locked || !dirty || (raw ? !preview : !configured)}
          onClick={() => void run("save", async () => {
            const next = await saveProxy({ ...(raw ? { raw } : {}), enabled,
              use_clash: useClash, clash_proxy_url: clashUrl.trim() });
            loadSettings(next);
            setPreview(null);
            setRaw("");
            setMessage({ color: "green", text: "已保存，后续读取配置的请求生效；已建立的连接保持原链路。" });
          })}>保存配置</Button>
        <Button variant="default" disabled={locked || dirty} loading={busy === "test"}
          onClick={() => void run("test", async () => {
            const result = await testProxy();
            setMessage({ color: "green", text: `连接成功：${ROUTES[result.mode]}；实测出口 IP ${result.ip}，耗时 ${result.elapsed_ms} ms。此测试不判断出口国家或 ChatGPT 可用性。` });
          })}>测试连接</Button>
      </Group>
      {dirty && <Text size="sm" c="dimmed">有未保存的修改，请先保存配置，再测试连接。</Text>}
      {message && <Alert color={message.color} variant="light"
        icon={message.color === "green" ? <IconCheck size={18} /> : <IconAlertCircle size={18} />}>
        {message.text}
      </Alert>}
    </Stack>
  );
}
