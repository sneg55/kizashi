import { Section } from '../../components/Section'

const BUILT_ON = [
  {
    name: 'Strands Agents SDK',
    role: 'the graph, the two agents, and the hook that owns the outbound call',
    wash: 'bg-accent-mist',
  },
  {
    name: 'Amazon Bedrock via the Mantle endpoint',
    role: 'the model that writes each brief from the record',
    wash: 'bg-flag-wash',
  },
  {
    name: 'Amazon EventBridge Scheduler and ECS Fargate',
    role: 'the monthly sweep, on the 7th at 12:00 UTC, publishing the report and the alert history to S3',
    wash: 'bg-mint-veil',
  },
  {
    name: 'Amazon SES and AgentCore Runtime',
    role: 'the delivery channel behind send_alert, and the entrypoint the same pipeline answers on',
    wash: 'bg-accent-wash',
  },
]

export function BuiltOn() {
  return (
    <Section title="Built on" align="center">
      <dl className="m-0 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {BUILT_ON.map((item) => (
          <div key={item.name} className="card p-6 sm:p-8">
            <span aria-hidden="true" className={`block h-10 w-10 rounded-full ${item.wash}`} />
            <dt className="mt-6 font-display text-lead font-medium tracking-[-0.01em] text-ink">
              {item.name}
            </dt>
            <dd className="m-0 mt-2 text-tiny text-ink-soft">{item.role}</dd>
          </div>
        ))}
      </dl>
    </Section>
  )
}
