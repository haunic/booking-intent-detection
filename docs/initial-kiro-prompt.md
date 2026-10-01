You are a senior full-stack engineer. Build a complete, responsive, locally hosted web application that demonstrates the TypeSafe SDK in an “intent to book” prediction use case for flight shopping.

Use the TypeSafe SDK documentation provided with this request as the primary source of truth (https://ollama.com/blog/ollama-now-supports-jev-style-decision-models, https://docs.typesafe.ai/sdk/python). Before implementing the SDK integration, inspect the documentation and the locally installed package to confirm:

1. The exact package name and import syntax
2. Whether the SDK is synchronous or asynchronous
3. How base URL, API key, and model are configured
4. The exact request and response schemas
5. Whether the SDK returns a probability or confidence score
6. How SDK errors and malformed model outputs should be handled

Do not invent unsupported SDK methods. Isolate all SDK-specific code in a dedicated adapter so it can be corrected easily if the installed SDK version differs from the documentation.

# 1. Objective

Create a responsive web application that runs entirely on my laptop and uses:

- A local Ollama server
- The locally installed `nimble` model
- The TypeSafe SDK
- Local JSON file storage only

The application predicts whether a traveler browsing an online travel agency or airline website has a High, Medium, or Low likelihood of completing a flight booking during the current browsing session.

This is a demonstration application, not a production booking engine.

# 2. Functional background

“Intent to book” represents how close a traveler appears to be to booking a flight.

Examples:

- High intent: the traveler has converged on exact travel parameters, repeated a query, is searching for near-term travel, or is interacting with fare, passenger, seat, or payment information.
- Medium intent: the traveler is comparing a narrow range of dates or prices while keeping the same route and similar trip duration.
- Low intent: the traveler is exploring broadly, changing destinations or dates significantly, or searching far in advance without converging on an itinerary.

A travel website could use this signal to decide whether to:

- Monetize a low-intent session with advertising
- Run more comprehensive and potentially expensive flight searches for a high-intent traveler
- Return more accurate prices and broader airline content for high-intent sessions

# 3. Technical constraints

The application must:

- Run locally on a laptop
- Connect to Ollama at a configurable local URL
- Use the `nimble` model by default
- Use the TypeSafe SDK for prediction
- Be responsive on desktop, tablet, and mobile
- Not use a database
- Persist all mutable data under `./data/`
- Continue to work after an application restart
- Use JSON files with atomic writes where practical
- validate all JSON before saving it
- sanitize user input and rendered model output
- avoid hardcoding secrets in source code
- include clear local setup and run instructions in `README.md`

Choose a simple, maintainable full-stack architecture suitable for a local demonstration. Prefer a single repository and the smallest reasonable dependency set.

If no technology stack was specified, select one and document the decision before implementation. A preferred option is:

- Frontend: React with TypeScript
- Backend: Node.js with TypeScript
- Shared validation and types between frontend and backend
- Runtime schema validation with a library such as Zod
- CSS framework or component library only if it improves responsiveness without adding unnecessary complexity

The TypeSafe SDK must only be called from the backend. The browser must never access or modify files directly.

# 4. Main navigation

Provide the following main areas:

1. New Test Session
2. Session History
3. Administration

The currently selected session should remain available when navigating between relevant pages.

# 5. Session lifecycle

A user must be able to:

- Start a new test session
- Choose a search mode
- Manually enter session data
- Randomly pre-populate realistic test session data
- Add or remove previous searches or messages
- Save a session without running a prediction
- Run an intent-to-book prediction
- View the human-readable result
- View the raw TypeSafe SDK JSON response
- Retrieve and reopen a previous session
- Modify a retrieved session
- Run another prediction
- See previous prediction runs for that session
- Duplicate a previous session into a new test session
- Delete a session after confirmation

Every session must have at least:

- Unique session ID
- Search mode
- Creation timestamp
- Last updated timestamp
- Browsing date and local time
- Browsing time zone or UTC offset
- Device/channel
- Input data
- Prediction history
- Last prediction status
- Optional user-friendly session name

Use ISO 8601 for stored timestamps.

Supported browsing channels:

- Mobile
- Desktop
- Voice AI Assistant

# 6. Random test-data generation

Add a “Generate random session” button.

It must create coherent, realistic data instead of independently random fields.

Examples of coherence rules:

- Airport codes must be valid-looking three-letter IATA codes from a small local reference list.
- Origin and destination must differ.
- Departure must not be before the browsing date.
- Return must not be before departure.
- Passenger counts must be valid.
- At least one adult should be present unless the UI explicitly supports another valid rule.
- Previous searches should generally occur before the current search.
- Previous searches may show route convergence, date convergence, or broad exploration.
- Conversational messages should correspond to the structured facts where relevant.
- Random generation should produce a useful mix of expected High, Medium, and Low examples.

Provide an optional intent profile selector for generated data:

- Random
- Likely High
- Likely Medium
- Likely Low

This selector influences generated test data only. It must not directly set the prediction result.

# 7. Mode A: Traditional Flight Search

The Traditional Flight Search screen must contain:

## Session context

- Browsing date
- Browsing local time
- Time zone or UTC offset
- Device/channel

## Previous searches

Support between 0 and 10 previous searches.

Each previous search contains:

- Origin
- Destination
- Departure date
- Return date
- Number of adults
- Number of children

The UI must allow the user to:

- Add a previous search
- Remove a previous search
- Reorder previous searches if useful
- Copy a previous search into the current search
- Clearly see the chronological order

## Current search

Fields:

- Origin
- Destination
- Departure date
- Return date
- Number of adults
- Number of children

Apply inline validation and accessible error messages.

Derive and display useful calculated values where possible:

- One-way or round-trip
- Length of stay
- Days between browsing date and departure
- Differences from the most recent previous search

# 8. Mode B: Conversational Flight Search

The Conversational Flight Search screen must mimic a simple chat interface.

It must contain:

## Session context

- Browsing date
- Browsing local time
- Time zone or UTC offset
- Device/channel

## Previous conversation

Support 0 to 10 previous traveler requests.

Each request is natural-language text and may include:

- Origin
- Destination
- Departure date
- Return date
- Number of adults
- Number of children
- Flexible dates
- Budget preferences
- Exploration language
- Urgency or readiness language

The UI must allow the user to:

- Add a previous message
- Remove a previous message
- Edit a previous message
- See messages in chronological order

## Current request

Provide a multiline free-text input styled like a chatbot composer.

Example:

“Find me a return flight from Nice to Bangkok for two adults, leaving around 15 December and coming back one week later.”

The prediction must use the full conversation history and current request. Do not require perfect extraction of structured travel fields unless this is required by the SDK. The backend should build a faithful state description from the complete conversation.

# 9. Prediction workflow

In both modes, provide a prominent button labeled:

“Predict intent to book”

When clicked, the backend must:

1. Validate the active session.
2. Load the correct mode-specific JSON configuration from `./data/config/`.
3. Load the current TypeSafe connection settings.
4. Convert the session into a concise but complete natural-language `state`.
5. Inject that state into the configured TypeSafe request.
6. Call the TypeSafe SDK using the configured Ollama endpoint and model.
7. Validate and normalize the SDK response.
8. Save the request, normalized result, raw response, timestamps, duration, and errors in the session’s prediction history.
9. Return the result to the frontend.

Do not send empty, undefined, or contradictory values in the generated state.

The generated state should include relevant derived information such as:

- Browsing channel
- Browsing date and local time
- Time zone
- Current itinerary
- Previous itinerary or conversation history
- Days before departure
- Trip duration
- Route changes
- Date changes
- Passenger-count changes
- Evidence of convergence or exploration

# 10. Prediction result display

After a successful prediction, display:

## Human-readable result

- Intent to book: High, Medium, or Low
- Probability or confidence, as a percentage if the SDK provides a valid score
- A short natural-language explanation based on the SDK response
- Prediction timestamp
- Model used
- Response duration

Use a clear visual status:

- High: positive/high-intent styling
- Medium: neutral/caution styling
- Low: low-intent styling

Do not communicate certainty that is not present in the model response.

## Raw result

Show the complete raw JSON response returned by the TypeSafe SDK in a formatted, collapsible JSON viewer with a copy button.

Also show, in a separate collapsible section:

- The final TypeSafe request sent to the SDK
- The generated `state`
- The normalized application result

If the TypeSafe SDK does not return a probability or confidence score:

- Do not fabricate one.
- Display “Probability not provided by the model.”
- Preserve the raw response.
- Keep the normalized intent classification if it is valid.

The normalized application result should follow this shape:

{
  "intent": "High | Medium | Low",
  "probability": 0.0,
  "probabilityAvailable": true,
  "explanation": "string",
  "model": "string",
  "predictedAt": "ISO-8601 timestamp",
  "durationMs": 0
}

When probability is unavailable, set:

{
  "probability": null,
  "probabilityAvailable": false
}

# 11. Administration page

Create an Administration page with two sections.

## 11.1 Connection settings

Allow the user to load, edit, validate, and persist:

- `TYPESAFE_BASE_URL`
  - Default: `http://localhost:11434`
- `TYPESAFE_API_KEY`
  - Default: `ollama`
- `TYPESAFE_DEFAULT_MODEL`
  - Default: `nimble`

Store these settings locally under `./data/config/`.

Requirements:

- Mask the API key field by default.
- Add a show/hide control.
- Add a “Test connection” button.
- Report clear success or failure information.
- Add a “Reset to local defaults” button.
- Ask for confirmation before resetting.
- Resetting must restore the three default values above.
- Do not log or expose the API key unnecessarily.

The connection test should verify, when supported:

- Ollama endpoint availability
- Model availability
- TypeSafe SDK connectivity

If model availability cannot be checked through the TypeSafe SDK, use an appropriate local Ollama endpoint from the backend and clearly separate that check from the prediction call.

## 11.2 Model configurations

Maintain two independent JSON configuration files:

- `./data/config/traditional-flight-search.json`
- `./data/config/conversational-flight-search.json`

The Administration page must allow the user to:

- Select either configuration
- Load the current JSON
- Edit it in a code editor or formatted text area
- Validate JSON syntax
- Validate the required application schema
- Save valid JSON
- Reject invalid JSON with line-level or actionable errors
- Reset each file to its default
- Download or copy the current JSON if easy to support
- See when the configuration was last modified

Preserve unknown valid fields where possible so that SDK-specific extensions are not lost.

# 12. Default model configuration

Create a separate default configuration for each mode. Seed both files on first run if they do not exist.

Use valid JSON. Do not HTML-encode comparison operators inside JSON strings.

## Traditional Flight Search default

{
  "model": "nimble",
  "state": "",
  "questions": {
    "booking_intent": {
      "type": "choice",
      "instructions": "Evaluate the likelihood that the traveler will complete a flight booking during the current search session based on session behavior and search parameters.",
      "criteria": {
        "High": "Traveler has converged on exact travel parameters, repeated an identical flight query, viewed specific seat or fare rules, entered passenger or payment details, or is booking urgent or near-term travel.",
        "Medium": "Traveler is testing slight date variations of approximately two to five days with the same origin and destination, comparing narrow pricing options, or maintaining similar stay durations across repeated searches.",
        "Low": "Traveler is in an early exploration stage, with a long advance booking window, broad destination switching, major date shifts, or browsing behavior that does not show a narrowed itinerary."
      }
    }
  }
}

## Conversational Flight Search default

{
  "model": "nimble",
  "state": "",
  "questions": {
    "booking_intent": {
      "type": "choice",
      "instructions": "Evaluate the likelihood that the traveler will complete a flight booking during the current search session based on session behavior and search parameters.",
      "criteria": {
        "High": "Traveler has converged on exact travel parameters, repeated an identical flight query, viewed specific seat or fare rules, entered passenger or payment details, or is booking urgent or near-term travel.",
        "Medium": "Traveler is testing slight date variations of approximately two to five days with the same origin and destination, comparing narrow pricing options, or maintaining similar stay durations across repeated searches.",
        "Low": "Traveler is in an early exploration stage, with a long advance booking window, broad destination switching, major date shifts, or browsing behavior that does not show a narrowed itinerary."
      }
    }
  }
}