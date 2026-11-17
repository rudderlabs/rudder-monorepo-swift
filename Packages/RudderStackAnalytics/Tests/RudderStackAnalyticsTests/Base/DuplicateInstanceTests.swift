//
//  DuplicateInstanceTests.swift
//  RudderStackAnalyticsTests
//

import Foundation
import Testing
@testable import RudderStackAnalytics

@Suite("Duplicate Instance Tests")
struct DuplicateInstanceTests {

    private let refusedMessage = "An instance for this write key already runs in this process"

    private func makeAnalytics(writeKey: String, logger: MockLogger = MockLogger()) -> Analytics {
        let config = MockProvider.createMockConfiguration(writeKey: writeKey)
        config.trackApplicationLifecycleEvents = false
        config.sessionConfiguration.automaticSessionTracking = false
        config.logger = logger
        return Analytics(configuration: config)
    }

    @Test("given a running instance, when a second instance starts for its write key, then the second logs one error and ignores calls, and the first keeps sending")
    func testSecondInstanceIsRefused() async {
        let writeKey = MockConstant.mockWriteKey
        let firstLogger = MockLogger()
        let secondLogger = MockLogger()
        let first = makeAnalytics(writeKey: writeKey, logger: firstLogger)
        let firstPlugin = MockEventCapturePlugin()
        first.add(plugin: firstPlugin)

        let second = makeAnalytics(writeKey: writeKey, logger: secondLogger)
        second.track(name: "from second")
        first.track(name: "from first")

        let events = await firstPlugin.waitForEvents(TrackEvent.self, timeout: 1)
        #expect(events.map(\.event) == ["from first"])
        #expect(!first.isAnalyticsShutdown)
        #expect(second.isAnalyticsShutdown)
        #expect(secondLogger.logs.filter { $0.message.contains(refusedMessage) }.count == 1)
        #expect(!firstLogger.hasLog(level: "ERROR", containing: refusedMessage))
        first.shutdown()
    }

    @Test("given a refused instance, when it shuts down, then the running instance keeps the write key")
    func testRefusedInstanceDoesNotFreeWriteKey() {
        let writeKey = MockConstant.mockWriteKey
        let first = makeAnalytics(writeKey: writeKey)
        let refused = makeAnalytics(writeKey: writeKey)

        refused.shutdown()
        let third = makeAnalytics(writeKey: writeKey)

        #expect(!first.isAnalyticsShutdown)
        #expect(third.isAnalyticsShutdown)
        first.shutdown()
    }

    @Test("given a running instance, when it stops, then a new instance for its write key starts",
          arguments: [false, true])
    func testStoppedInstanceFreesWriteKey(invalidWriteKey: Bool) {
        let writeKey = MockConstant.mockWriteKey
        let first = makeAnalytics(writeKey: writeKey)
        let logger = MockLogger()

        if invalidWriteKey {
            first.handleInvalidWriteKey()
        } else {
            first.shutdown()
        }
        let next = makeAnalytics(writeKey: writeKey, logger: logger)

        #expect(!next.isAnalyticsShutdown)
        #expect(!logger.hasLog(level: "ERROR", containing: refusedMessage))
        next.shutdown()
    }

    @Test("given instances for different write keys, when they start, then both run")
    func testDifferentWriteKeysBothRun() {
        let logger = MockLogger()
        let first = makeAnalytics(writeKey: MockConstant.mockWriteKey, logger: logger)
        let second = makeAnalytics(writeKey: MockConstant.mockWriteKey, logger: logger)

        #expect(!first.isAnalyticsShutdown)
        #expect(!second.isAnalyticsShutdown)
        #expect(!logger.hasLog(level: "ERROR", containing: refusedMessage))
        first.shutdown()
        second.shutdown()
    }

    @Test("given many threads, when each starts an instance for one write key, then exactly one instance runs")
    func testConcurrentStartsKeepOneInstance() {
        let writeKey = MockConstant.mockWriteKey
        let lock = NSLock()
        var instances: [Analytics] = []

        DispatchQueue.concurrentPerform(iterations: 8) { _ in
            let analytics = makeAnalytics(writeKey: writeKey)
            lock.lock()
            instances.append(analytics)
            lock.unlock()
        }

        let running = instances.filter { !$0.isAnalyticsShutdown }
        #expect(running.count == 1)
        running.forEach { $0.shutdown() }
    }
}
