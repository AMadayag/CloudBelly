import type { Datastore, Dataset } from "./domain.js"

function getDataSetFromId(id: String): Dataset | null {
  const ds: Datastore = { datasets: []} // replace with actual pull from db
  
  for (const i of ds.datasets) {
    if (i.DataSetID === id) {
      return i;
    }
  }

  return null;
}
