//
//  LibraryInfoPluginTests.swift
//  RudderStackAnalyticsTests
//
//  Created by Satheesh Kannan on 13/12/24.
//

import Testing
@testable import RudderStackAnalytics

@Suite("LibraryInfoPlugin Tests")
class LibraryInfoPluginTests {
    var libraryInfoPlugin: LibraryInfoPlugin
    
    init() {
        self.libraryInfoPlugin = LibraryInfoPlugin()
    }
    
    @Test("when intercepting different events, then adds library context information", arguments: [
        MockProvider.mockTrackEvent as Event,
        MockProvider.mockScreenEvent as Event,
        MockProvider.mockIdentifyEvent as Event,
        MockProvider.mockGroupEvent as Event,
        MockProvider.mockAliasEvent as Event
    ])
    func testPluginIntercept(_ event: Event) {
        let analytics = MockProvider.createMockAnalytics()
        libraryInfoPlugin.setup(analytics: analytics)
        
        let result = libraryInfoPlugin.intercept(event: event)
        
        #expect(result != nil)
        #expect(result?.context != nil)
        guard let context = result?.context?.rawDictionary else {
            Issue.record("Event context not found")
            return
        }
        
        #expect(context["library"] != nil)
        guard let libraryInfo = context["library"] as? [String: Any] else {
            Issue.record("Library info not found")
            return
        }
        
        #expect(libraryInfo["name"] != nil)
        #expect(libraryInfo["version"] as? String == RudderStackAnalyticsVersion.current)
    }
    
    @Test("given a wrapper library, when intercepting an event, then adds wrapperLibrary next to the unchanged library context")
    func testWrapperLibraryIsAdded() throws {
        let plugin = LibraryInfoPlugin(wrapperLibraryInfo: { (name: "rudder-sdk-flutter", version: "4.0.0") })
        plugin.setup(analytics: MockProvider.createMockAnalytics())

        let context = try #require(plugin.intercept(event: MockProvider.mockTrackEvent)?.context?.rawDictionary)

        let wrapperLibrary = try #require(context["wrapperLibrary"] as? [String: String])
        #expect(wrapperLibrary == ["name": "rudder-sdk-flutter", "version": "4.0.0"])
        let library = try #require(context["library"] as? [String: String])
        #expect(library == ["name": RSLibraryName, "version": RSVersion])
    }

    @Test("given no wrapper library, when intercepting an event, then adds no wrapperLibrary")
    func testNoWrapperLibrary() throws {
        let plugin = LibraryInfoPlugin(wrapperLibraryInfo: { nil })
        plugin.setup(analytics: MockProvider.createMockAnalytics())

        let context = try #require(plugin.intercept(event: MockProvider.mockTrackEvent)?.context?.rawDictionary)

        #expect(context["wrapperLibrary"] == nil)
        #expect(context["library"] != nil)
    }

    @Test("when setup is called, then analytics reference is stored")
    func testPluginSetup() {
        let analytics = MockProvider.createMockAnalytics()
        
        libraryInfoPlugin.setup(analytics: analytics)
        
        #expect(libraryInfoPlugin.analytics != nil)
        #expect(libraryInfoPlugin.pluginType == .preProcess)
    }
}
