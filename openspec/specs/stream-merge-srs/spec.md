# Stream Merge & SRS

## Purpose

Server pulls raw audio and video streams from the RTMP server, merges them with
FFmpeg, and publishes the merged View stream back to SRS for Web playback.

## Requirements

### Requirement: Server pulls raw streams using the shared normalized stream name

Server SHALL build raw RTMP pull URLs with the same stream naming rule used by
Node when it publishes raw streams:

```text
stream_name = device_name.replace(" ", "_") + "_" + device_type + "_" + server_device_id
```

`server_device_id` SHALL be the Server database id for the selected
`VideoDevice` or `AudioDevice`. In Server APIs and WSS commands this value is
named `device_id`.

The raw pull URL SHALL be:

```text
rtmp://{RTMP_HOST}:{RTMP_PORT}/live/{stream_name}
```

`RTMP_DEBUG=true` SHALL force the RTMP host to the local debug target.

#### Scenario: Pull URL for a video device

- **WHEN** `RTMP_HOST=127.0.0.1`, `RTMP_PORT=1935`, the device name is `Integrated Camera`, `device_type=video`, and `device_id=1`
- **THEN** Server builds `rtmp://127.0.0.1:1935/live/Integrated_Camera_video_1`

#### Scenario: Pull URL for an audio device

- **WHEN** `RTMP_HOST=127.0.0.1`, `RTMP_PORT=1935`, the device name is `Microphone Array`, `device_type=audio`, and `device_id=2`
- **THEN** Server builds `rtmp://127.0.0.1:1935/live/Microphone_Array_audio_2`

### Requirement: Merge waits for raw RTMP inputs

Server SHALL start the merge FFmpeg process only after both selected raw RTMP
inputs are reachable. Readiness SHALL be verified by probing the RTMP data plane
rather than repeatedly asking Node over WSS.

#### Scenario: Raw streams become reachable

- **WHEN** Node accepts `UPDATE_STREAM=true` and publishes raw audio/video streams
- **THEN** Server retries RTMP probes until both inputs are reachable or the configured timeout expires
- **AND** Server starts the merge process only after both inputs are reachable

#### Scenario: Raw stream timeout

- **WHEN** at least one selected raw RTMP input remains unreachable until timeout
- **THEN** Server fails View creation and reports the unavailable raw pull URL

### Requirement: FFmpeg merges audio and video streams

Server SHALL use an FFmpeg subprocess to merge the selected raw video and audio
inputs into one FLV/RTMP output stream.

#### Scenario: Start merge process

- **WHEN** View creation succeeds for `view_id=1`
- **THEN** Server starts an FFmpeg subprocess with the selected video and audio raw RTMP URLs as inputs
- **AND** Server publishes the output to `rtmp://{SRS_HOST}:{SRS_RTMP_PORT}/view/1`

### Requirement: Server publishes merged View streams to SRS

Server SHALL build merged View push URLs through the RTMP pusher module. Push
URLs SHALL use the internal SRS endpoint configured by `SRS_HOST` and
`SRS_RTMP_PORT`.

#### Scenario: Production push URL

- **WHEN** `SRS_HOST=stream-server`, `SRS_RTMP_PORT=1935`, and `view_id=1`
- **THEN** Server pushes to `rtmp://stream-server:1935/view/1`

### Requirement: Server returns playback URLs for Views

Server SHALL return SRS playback URLs in View responses. Playback URLs SHALL use
the public SRS endpoint configured by `SRS_PUBLIC_HOST`,
`SRS_PUBLIC_RTMP_PORT`, and `SRS_PUBLIC_HTTP_PORT`. When these public values are
not configured, Server SHALL fall back to `SRS_HOST`, `SRS_RTMP_PORT`, and
`SRS_HTTP_PORT`.

#### Scenario: Playback URL response

- **WHEN** `SRS_HOST=stream-server`, `SRS_PUBLIC_HOST=10.126.59.25`, `SRS_PUBLIC_RTMP_PORT=1935`, `SRS_PUBLIC_HTTP_PORT=8082`, and `view_id=1`
- **THEN** Server returns `rtmp://10.126.59.25:1935/view/1`
- **AND** Server returns HTTP-FLV and WebRTC playback URLs on `10.126.59.25:8082`
