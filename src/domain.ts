export interface Datastore {
  datasets: Dataset[]
}

export interface Dataset {
  Datasource: String,
  DataSetType: DataSetType,
  DataSetID: String,
  TimeObject: TimeObject,
  Locations: Location[],
  Events: Event[]
}

export interface Event {
  eventID: String,
  eventType: EventType,
  TimeObject: TimeObject,
  Attributes: Attributes
}

export interface Attributes {
  price: number,
  suburb: Suburb,
  state: State,
  bedrooms?: number,
}

export enum EventType {
  AVG_HOUSE_PRICE
}

export interface TimeObject {
  timestamp: Date,
  duration?: number, // datasets don't have a duration but events do??
  timezone: Location
}

export interface Location {
  city: String,
  state: State
}

export enum Suburb {
  CASTLE_HILL
}

export enum State {
  NSW,
  VIC,
  QLD,
  SA,
  WA,
  NT
}

export enum DataSetType {
  PROPERTY_SALES
}