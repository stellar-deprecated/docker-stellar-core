local cj    = require "cjson"
local dt    = require "date_time"
local l     = require "lpeg"
local table = require "table"
local math  = require "math"

local environment = read_config("environment")
local node = read_config("node")
local cluster = read_config("cluster")

-- how many metrics to load into a single influx/atlas payload
local max_metrics = read_config("max_metrics") or 80

local latest_stats = {}

function process_message()
  local raw_message = read_message("Payload")
  local ok, json = pcall(cj.decode, raw_message)

  if not ok then return -1 end

  if json["ts"] ~= nil then
     local ts = lpeg.match(dt.rfc3339, json["ts"])
     if not ts then return -1 end

     local timestamp = dt.time_to_ns(ts)
  end

  for name, stats in pairs(json["metrics"]) do
    if stats.type == "timer" then
      process_metric(timestamp, name, stats, {
        "count", "1_min_rate",
        "min", "mean", "max", "95%", "99%", "99.9%"
      })
    elseif stats.type == "meter" then
      process_metric(timestamp, name, stats, {
        "count", "1_min_rate",
      })
    elseif stats.type == "counter" then
      process_metric(timestamp, name, stats, {
        "count"
      })
    end
  end

  return 0
end

function send_to_influx(ns)
  local time = math.floor(ns / 1000000)
  local output = {}

  local queued_metrics = 0

  for name, stats in pairs(latest_stats) do
    if queued_metrics >= max_metrics then
      inject_for_influx(ns, output)
      output = {}
      queued_metrics = 0
    end

    name = environment .. "." .. node .. "." .. name

    local point_set = {
      name = name,
      columns = {"time"},
      points = {{time}}
    }

    for stat, value in pairs(stats) do
      table.insert(point_set.columns, stat)
      table.insert(point_set.points[1], value)
    end

    table.insert(output, point_set)
    queued_metrics = queued_metrics + 1
  end

  inject_for_influx(ns, output)
end

function inject_for_influx(ns, output)
  if next(output) then
    local message = {
      Timestamp = ns,
      Type = "stellar.core.metrics.influx"
    }

    message.Payload = cjson.encode(output)

    inject_message(message)
  end
end

function send_to_atlas(ns)
  local time = math.floor(ns / 1000000)
  local output = {
    tags = {
      environment = environment,
      cluster = cluster,
      node = node,
      app = "stellar-core"
    },
    metrics = {
    }
  }

  local queued_metrics = 0

  for name, stats in pairs(latest_stats) do
    if queued_metrics >= max_metrics then
      inject_for_atlas(ns, output)
      output.metrics = {}
      queued_metrics = 0
    end
    for stat, value in pairs(stats) do
      local metric_payload = {
        tags = {
          name = name,
          stat = stat,
          ["atlas.dstype"] = "gauge"
        },
        timestamp = time,
        value = value
      }
      table.insert(output.metrics, metric_payload)
    end
    queued_metrics = queued_metrics + 1
  end

  inject_for_atlas(ns, output)
end

function inject_for_atlas(ns, output)
  if next(output.metrics) then
    local message = {
      Timestamp = ns,
      Type = "stellar.core.metrics.atlas"
    }

    message.Payload = cjson.encode(output)

    inject_message(message)
  end
end

function timer_event(ns)
  send_to_influx(ns)
  send_to_atlas(ns)
end

function process_metric(timestamp, name, stats, stat_whitelist)
  local selected_stats = {}

  for i, stat in ipairs(stat_whitelist) do
    selected_stats[stat] = stats[stat]
  end

  latest_stats[name] = selected_stats
end
