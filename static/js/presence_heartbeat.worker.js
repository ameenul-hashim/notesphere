/**
 * NoteSphere Presence Heartbeat Worker
 * ─────────────────────────────────────────────────────────────────────────────
 * A dedicated Web Worker that pings the main thread on a fixed interval.
 *
 * Browser tabs throttle setInterval to ~1/min when hidden, which would cause
 * background tabs to be considered stale and dropped from presence. Timers in a
 * dedicated worker are not throttled the same way, so a hidden tab keeps
 * heartbeatting normally and stays online. If the laptop sleeps or the browser
 * crashes, the worker stops too and the session is reaped after the timeout.
 */
'use strict';

var HEARTBEAT_MS = 20000;

setInterval(function () {
  self.postMessage('tick');
}, HEARTBEAT_MS);
