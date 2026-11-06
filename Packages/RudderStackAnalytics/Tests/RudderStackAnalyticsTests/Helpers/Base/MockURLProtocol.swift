//
//  MockURLProtocol.swift
//  RudderStackAnalyticsTests
//
//  Created by Satheesh Kannan on 22/08/25.
//

import Foundation

/**
 A `URLProtocol` subclass for mocking HTTP responses in tests.
 */
final class MockURLProtocol: URLProtocol {
    
    typealias RequestHandler = (URLRequest) throws -> (Int, Data?, [String: String]?)
    
    /**
     Closure the test sets to provide a mocked response.
     - Returns: `(statusCode, responseData, headers)`
     */
    static var requestHandler: RequestHandler? {
        get { locked { storedRequestHandler } }
        set { locked { storedRequestHandler = newValue } }
    }
    
    /**
     When `false` (default), GET requests return 200 empty even if `requestHandler` is set.
     This absorbs background source config downloads spawned by `Analytics` initialization.
     Tests that need GET requests to reach the handler (e.g. SourceConfigProviderTests)
     must set this to `true`.
     */
    static var forwardGetRequestsToHandler: Bool {
        get { locked { storedForwardGetRequestsToHandler } }
        set { locked { storedForwardGetRequestsToHandler = newValue } }
    }
    
    /**
     The host of the test that owns `requestHandler`, or `nil` when any host may reach it.
     A request to another host gets an empty 200 instead, so an uploader that an earlier test left running
     cannot reach the current test's handler.
     */
    static var ownerHost: String? {
        get { locked { storedOwnerHost } }
        set { locked { storedOwnerHost = newValue } }
    }
    
    /**
     Runs `body` while no other thread reads or changes the mock state. Requests arrive on URLSession threads,
     and a test instance can be torn down on another thread while the next test sets up, so setup and teardown
     check and change the state in one step. Recursive, so `body` can use the properties above.
     */
    static func locked<T>(_ body: () throws -> T) rethrows -> T {
        lock.lock()
        defer { lock.unlock() }
        return try body()
    }
    
    private static let lock = NSRecursiveLock()
    private static var storedRequestHandler: RequestHandler?
    private static var storedForwardGetRequestsToHandler = false
    private static var storedOwnerHost: String?
    
    // MARK: - URLProtocol overrides
    
    override class func canInit(with request: URLRequest) -> Bool {
        // Intercept all requests
        return true
    }
    
    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }
    
    override func startLoading() {
        // One snapshot of the owner and the handler, so a request cannot pass the owner check and then
        // read a handler that the next test installed in between. The handler runs outside the lock.
        let (ownerHost, handler, forwardGetRequests) = MockURLProtocol.locked {
            (MockURLProtocol.storedOwnerHost, MockURLProtocol.storedRequestHandler,
             MockURLProtocol.storedForwardGetRequestsToHandler)
        }
        
        if let ownerHost, request.url?.host != ownerHost {
            respondWithEmptySuccess()
            return
        }
        
        // GET requests return 200 empty unless the test explicitly opts in.
        // This absorbs background source config downloads (GET /sourceConfig)
        // that Analytics initialization spawns asynchronously, preventing them from
        // going through the test's handler and corrupting callCount/attemptCount.
        //
        // POST requests with no handler stay pending — no success (batches not deleted)
        // and no failure (no retry loop).
        if request.httpMethod == "GET" && (handler == nil || !forwardGetRequests) {
            respondWithEmptySuccess()
            return
        }
        
        guard let handler else {
            // POST with no handler: keep pending
            return
        }
        
        do {
            let (statusCode, data, headers) = try handler(request)
            
            guard let url = request.url else {
                client?.urlProtocol(self, didFailWithError: URLError(.badURL))
                return
            }
            
            // Safely build HTTPURLResponse
            if let response = HTTPURLResponse(
                url: url,
                statusCode: statusCode,
                httpVersion: "HTTP/1.1",
                headerFields: headers
            ) {
                client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            } else {
                client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
                return
            }
            
            // Send body if available
            if let data = data {
                client?.urlProtocol(self, didLoad: data)
            }
            
            client?.urlProtocolDidFinishLoading(self)
            
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }
    
    override func stopLoading() {
        /* Default implementation (no-op) */
    }
    
    private func respondWithEmptySuccess() {
        if let url = request.url,
           let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: nil) {
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocolDidFinishLoading(self)
        }
    }
}
