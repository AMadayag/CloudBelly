interface Datasets {
  Datasource: String,
  DataSetType: DataSetType,
  DataSetID: String,
  TimeObject: TimeObject,
  Locations: Location[],
  Events: Event[]
}

interface Event {
  eventID: String,
  eventType: EventType,
  TimeObject: TimeObject,
  Attributes: Attributes
}

interface Attributes {
  price: number,
  suburb: Suburb,
  state: State,
  bedrooms?: number,
}

enum EventType {
  AVG_HOUSE_PRICE
}

interface TimeObject {
  timestamp: Date,
  duration?: number, // datasets don't have a duration but events do??
  timezone: Location
}

interface Location {
  city: String,
  state: State
}

enum Suburb {
  CASTLE_HILL
}

enum State {
  NSW,
  VIC,
  QLD,
  SA,
  WA,
  NT
}

enum DataSetType {
  PROPERTY_SALES
}