// Shared by image pickers and Frame views; reject undecodable images before staging.
export async function readPreviewImage(file) {
  const url=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onerror=reject;reader.onload=()=>resolve(reader.result);reader.readAsDataURL(file)})
  await new Promise((resolve,reject)=>{const image=new Image();image.onload=resolve;image.onerror=reject;image.src=url})
  return url
}
