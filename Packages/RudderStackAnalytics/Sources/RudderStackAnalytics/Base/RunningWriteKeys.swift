//
//  RunningWriteKeys.swift
//  RudderStackAnalytics
//

import Foundation

// MARK: - RunningWriteKeys
/**
 The write keys that a running instance in this process holds.

 Two instances for one write key share one store, and break each other's uploads.
 So one write key has at most one running instance.
 The map holds a weak reference, so it does not keep an instance in memory.
 */
enum RunningWriteKeys {

    @Synchronized private static var instances: [String: WeakAnalytics] = [:]

    /**
     Records `analytics` for its write key. Returns `false` when another running instance already holds it.
     */
    static func claim(_ analytics: Analytics) -> Bool {
        let writeKey = analytics.configuration.writeKey
        var claimed = false
        $instances.modify { instances in
            let holder = instances[writeKey]?.analytics
            claimed = holder == nil || holder?.isAnalyticsShutdown == true
            if claimed {
                instances[writeKey] = WeakAnalytics(analytics: analytics)
            }
        }
        return claimed
    }

    /**
     Frees the write key of `analytics`, when `analytics` holds it.
     */
    static func release(_ analytics: Analytics) {
        let writeKey = analytics.configuration.writeKey
        $instances.modify { instances in
            if instances[writeKey]?.analytics === analytics {
                instances[writeKey] = nil
            }
        }
    }
}

private struct WeakAnalytics {
    weak var analytics: Analytics?
}
