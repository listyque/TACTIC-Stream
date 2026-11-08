const partSize = 16 * 1024 * 1024;

export async function publicationRequest(job, action, values, part, signal) {
  const payload = { ticket: job.ticket, project: job.project, ...values };
  let body = JSON.stringify(payload);
  if (part) {
    body = new FormData();
    for (const [key, value] of Object.entries(payload))
      body.append(
        key,
        typeof value === 'string' ? value : JSON.stringify(value)
      );
    body.append('file', part, 'part');
  }
  const response = await fetch('/admin/checkin-queue/' + action, {
    method: 'POST',
    body,
    signal,
    cache: 'no-store',
    headers: part ? undefined : { 'Content-Type': 'application/json' }
  });
  const data = await response.json().catch(() => null);
  if (!response.ok || !data?.result) {
    const error = new Error(data?.error || 'Check-in queue request failed.');
    error.status = response.status;
    throw error;
  }
  return data.result;
}

export async function stagePublication(job, signal, progress) {
  const { batch, options } = job.submission;
  const files = [...job.files, ...job.previews].slice(
    0,
    options.source_files.length
  );
  for (const [index, file] of files.entries()) {
    for (
      let offset = 0;
      offset < file.size || offset === 0;
      offset += partSize
    ) {
      await publicationRequest(
        job,
        'submit',
        {
          batch_id: batch,
          chunk_id: `file-${index}-${offset}`,
          operations:
            index === 0 && offset === 0
              ? [{ operation_id: 'publish', options }]
              : [],
          pieces: [{ operation_id: 'publish', file_index: index, offset }]
        },
        file.slice(offset, offset + partSize),
        signal
      );
      progress(
        (index +
          (file.size ? Math.min(1, (offset + partSize) / file.size) : 1)) /
          files.length
      );
    }
  }
}
