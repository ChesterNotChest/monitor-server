/**
 * Embedded RTMP server for local DEBUG_WEB_STREAM verification.
 *
 * Accepts ffmpeg RTMP pushes on  rtmp://127.0.0.1:1936/live/<stream-key>
 * Serves RTMP pulls on the same address for OBS / VLC.
 * HTTP on :8001 for status / flv playback.
 *
 * Launched automatically by Server when DEBUG_WEB_STREAM=true,
 * or manually:  node tools/rtmp_debug_server.js
 */

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

// Signal handling — must be registered BEFORE nms.run()
process.on('SIGINT', () => { nms.stop(); process.exit(0); });
process.on('SIGTERM', () => { nms.stop(); process.exit(0); });

console.log('[RTMP debug server] rtmp://127.0.0.1:1936/live');
nms.run();
