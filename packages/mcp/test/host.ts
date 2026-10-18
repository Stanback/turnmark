// Test host only: official AppBridge, opaque-origin sandbox, explicit tool forwarding.
import {
  AppBridge,
  PostMessageTransport,
} from "@modelcontextprotocol/ext-apps/app-bridge";
const state = window as any;
state.cards = [];
state.contexts = [];
state.calls = [];
state.delay = 0;
state.deny = false;
state.denyContext = false;
state.malformed = false;
state.mount = async (args: any, response: any, theme = "light") => {
  const iframe = document.createElement("iframe");
  iframe.title = "Turnmark comparison";
  iframe.setAttribute("sandbox", "allow-scripts");
  iframe.style.cssText = "width:100%;border:0;display:block;min-height:700px";
  document.body.append(iframe);
  const bridge = new AppBridge(
    null,
    { name: "Turnmark test host", version: "1" },
    { serverTools: {}, updateModelContext: {}, openLinks: {} },
    { hostContext: { theme, displayMode: "inline" } },
  );
  bridge.oncalltool = async (params) => {
    if (params.name !== "convert_swim") throw new Error("Tool not allowed");
    state.calls.push(params);
    if (state.delay)
      await new Promise((resolve) => setTimeout(resolve, state.delay));
    if (state.deny) throw new Error("Service busy");
    if (state.malformed)
      return {
        content: [],
        structuredContent: { status: "available", value: { time: "broken" } },
      };
    return state.callConversion(params);
  };
  bridge.onupdatemodelcontext = async (params) => {
    if (state.denyContext) throw new Error("Not supported");
    state.contexts.push(params);
    return {};
  };
  bridge.onopenlink = async () => {
    throw new Error("Denied");
  };
  bridge.onsizechange = ({ height }) => {
    iframe.style.height = `${height}px`;
  };
  bridge.oninitialized = async () => {
    await bridge.sendToolInput({ arguments: args });
    await bridge.sendToolResult(response);
  };
  await bridge.connect(
    new PostMessageTransport(iframe.contentWindow!, iframe.contentWindow!),
  );
  const html = await (await fetch("/card")).text();
  iframe.srcdoc = html.replace(
    "<head>",
    "<head><meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; frame-src 'none'\">",
  );
  state.cards.push(bridge);
};
