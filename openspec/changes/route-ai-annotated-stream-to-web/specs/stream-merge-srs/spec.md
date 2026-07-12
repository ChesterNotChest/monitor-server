# Stream Merge & SRS (Delta)

## MODIFIED Requirements

### Requirement: Server publishes merged View streams to SRS

Server SHALL build merged View push URLs through the RTMP pusher module. Push
URLs SHALL use the internal SRS endpoint configured by `SRS_HOST` and
`SRS_RTMP_PORT`.

AI 管线启动后，原始合流 SHALL 终止，AI 标注流 SHALL 推送到相同 RTMP app（`/live/`）。

#### Scenario: Production push URL

- **WHEN** `SRS_HOST=stream-server`, `SRS_RTMP_PORT=1935`, and `view_id=1`
- **THEN** Server pushes raw merge to `rtmp://stream-server:1935/live/1`
- **AND** AI pipeline (when active) pushes annotated stream to `rtmp://stream-server:1935/live/1`

### Requirement: Server returns playback URLs for Views

Server SHALL return SRS playback URLs in View responses. Playback URLs SHALL use
the public SRS endpoint configured by `SRS_PUBLIC_HOST`,
`SRS_PUBLIC_RTMP_PORT`, and `SRS_PUBLIC_HTTP_PORT`. When these public values are
not configured, Server SHALL fall back to `SRS_HOST`, `SRS_RTMP_PORT`, and
`SRS_HTTP_PORT`.

WebRTC WHEP URL SHALL use `app=live` to match the push target.

#### Scenario: Playback URL response

- **WHEN** `SRS_HOST=127.0.0.1`, `SRS_PUBLIC_HOST=127.0.0.1`, `SRS_RTMP_PORT=1935`, `SRS_HTTP_PORT=8082`, and `view_id=1`
- **THEN** Server returns `rtmp://127.0.0.1:1935/live/1`
- **AND** Server returns FLV URL `http://127.0.0.1:8082/live/1.flv`
- **AND** Server returns WebRTC WHEP URL `http://127.0.0.1:1985/rtc/v1/whep/?app=live&stream=1`
