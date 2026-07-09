"""source: node-media-server 本地 RTMP 靶子服务器。

Debug 模式下接收 Server 推来的合并 View 流，供 OBS 拉流测试。
复用 Node 项目 rtmp_server/index.js 的模式，端口改用 1936 避免冲突。
"""

const NodeMediaServer = require('node-media-server');

const config = {
  rtmp: {
    port: 1936,
    chunk_size: 60000,
    gop_cache: true,
    ping: 30,
    ping_timeout: 60,
  },
  http: {
    port: 8001,
    allow_origin: '*',
  },
};

const nms = new NodeMediaServer(config);
nms.run();

console.log('RTMP debug server running on rtmp://127.0.0.1:1936/live');
