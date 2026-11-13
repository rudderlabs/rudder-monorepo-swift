//
//  ObjCFacebookIntegrationTests.swift
//  RudderIntegrationFacebookTests
//

import Testing
import Foundation
@testable import RudderIntegrationFacebook

@Suite
struct ObjCFacebookIntegrationTests {

    private func makeWrapper() -> (ObjCFacebookIntegration, MockFacebookSettingsAdapter) {
        let settings = MockFacebookSettingsAdapter()
        let integration = FacebookIntegration(appEventsAdapter: MockFacebookAppEventsAdapter(), settingsAdapter: settings)
        return (ObjCFacebookIntegration(facebookIntegration: integration), settings)
    }

    @Test("given limited data use is on through the Obj-C wrapper, when the destination is disabled or missing and update gets an empty config, then the data processing options stay")
    func testEmptyUpdateKeepsDataProcessingOptions() {
        let (wrapper, settings) = makeWrapper()
        var error: NSError?
        #expect(wrapper.createWithDestinationConfig(["limitedDataUse": true, "dpoState": 1000, "dpoCountry": 1], error: &error))

        #expect(wrapper.updateWithDestinationConfig([:], error: &error))

        #expect(error == nil)
        #expect(settings.setDataProcessingOptionsCalls.count == 1)
        #expect(settings.setDataProcessingOptionsCalls[0].options == ["LDU"])
    }

    @Test("given the Obj-C wrapper, when an update sets limited data use explicitly, then it applies", arguments: [true, false])
    func testExplicitUpdateApplies(limitedDataUse: Bool) {
        let (wrapper, settings) = makeWrapper()
        var error: NSError?
        #expect(wrapper.createWithDestinationConfig(["limitedDataUse": !limitedDataUse], error: &error))

        #expect(wrapper.updateWithDestinationConfig(["limitedDataUse": limitedDataUse, "dpoState": 1000, "dpoCountry": 1], error: &error))

        #expect(error == nil)
        #expect(settings.setDataProcessingOptionsCalls.count == 2)
        #expect(settings.setDataProcessingOptionsCalls[1].options == (limitedDataUse ? ["LDU"] : []))
    }
}
