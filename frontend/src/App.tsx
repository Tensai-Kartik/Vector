import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { CommandDeck } from './components/CommandDeck';
import { MissionGraph } from './components/MissionGraph';
import { BrowserLab } from './components/BrowserLab';
import { EventStream } from './components/EventStream';
import { ActionInspector } from './components/ActionInspector';
import { AuditReport } from './components/AuditReport';
import { SettingsModal } from './components/SettingsModal';
import { BenchmarkModal } from './components/BenchmarkModal';
import { api } from './services/api';
import { MissionSocketClient } from './services/websocket';
import { MissionData, MissionEvent, MissionStepState, ExecutionReport } from './types';

export const App: React.FC = () => {
  const [demoMode, setDemoMode] = useState<boolean>(false);
  const [activeMissionId, setActiveMissionId] = useState<string | null>(null);
  const [missionStatus, setMissionStatus] = useState<string>('ready');
  const [steps, setSteps] = useState<MissionStepState[]>([]);
  const [events, setEvents] = useState<MissionEvent[]>([]);
  const [selectedStepId, setSelectedStepId] = useState<string | undefined>();
  const [currentUrl, setCurrentUrl] = useState<string>('about:blank');
  const [screencastFrame, setScreencastFrame] = useState<string | null>(null);
  const [activeActionIntent, setActiveActionIntent] = useState<string | undefined>();
  const [extractedData, setExtractedData] = useState<any[]>([]);
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const [report, setReport] = useState<ExecutionReport | undefined>();
  const [approvalRequired, setApprovalRequired] = useState<boolean>(false);

  // Modals
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isBenchmarksOpen, setIsBenchmarksOpen] = useState(false);

  // WebSocket client
  const socketClientRef = useRef<MissionSocketClient | null>(null);

  useEffect(() => {
    socketClientRef.current = new MissionSocketClient();
    return () => {
      socketClientRef.current?.disconnectAll();
    };
  }, []);

  const handleStartMission = async (params: {
    task: string;
    demo_mode: boolean;
    require_approval_for_high_risk: boolean;
    force_execution_method: 'browser' | 'api' | 'auto';
    open_browser_window?: boolean;
  }) => {
    // Reset state for new mission
    setSteps([]);
    setEvents([]);
    setReport(undefined);
    setExtractedData([]);
    setArtifacts([]);
    setSelectedStepId(undefined);
    setActiveActionIntent(undefined);
    setApprovalRequired(false);
    setMissionStatus('queued');

    try {
      const res = await api.createMission({
        task: params.task,
        demo_mode: params.demo_mode,
        require_approval_for_high_risk: params.require_approval_for_high_risk,
        force_execution_method: params.force_execution_method,
        open_browser_window: params.open_browser_window,
      });

      const mId = res.mission_id;
      setActiveMissionId(mId);

      // Connect WebSockets for events & screencast stream
      socketClientRef.current?.connectEvents(mId, (event: MissionEvent) => {
        setEvents((prev) => [...prev, event]);

        if (event.event_type === 'plan_generated' && event.details?.steps) {
          const parsedSteps = event.details.steps.map((s: any) => ({
            step_id: s.step_id,
            action_type: s.action_type,
            intent: s.intent,
            target_description: s.target_description,
            target_locator_value: s.target_locator_value,
            input_value: s.input_value,
            status: 'pending',
          }));
          setSteps(parsedSteps);
          setMissionStatus('running');

          const firstNav = event.details.steps.find((s: any) => s.action_type === 'navigate');
          if (firstNav?.input_value) {
            setCurrentUrl(firstNav.input_value);
          }
        }

        if (event.event_type === 'browser_action_started') {
          setActiveActionIntent(event.message);
          if (event.step_id) {
            setSteps((prev) =>
              prev.map((s) =>
                s.step_id === event.step_id ? { ...s, status: 'running' } : s
              )
            );
            setSelectedStepId(event.step_id);
          }
        }

        if (event.event_type === 'browser_action_completed') {
          if (event.details?.final_url) {
            setCurrentUrl(event.details.final_url);
          }
          if (event.step_id) {
            setSteps((prev) =>
              prev.map((s) =>
                s.step_id === event.step_id
                  ? {
                      ...s,
                      status: 'completed',
                      verification_status: 'passed',
                      verification_evidence: event.details?.evidence,
                    }
                  : s
              )
            );
          }
        }

        if (event.event_type === 'step_rejected') {
          if (event.step_id) {
            setSteps((prev) =>
              prev.map((s) =>
                s.step_id === event.step_id
                  ? {
                      ...s,
                      status: 'rejected',
                      validation_message: event.details?.error,
                    }
                  : s
              )
            );
          }
        }

        if (event.event_type === 'approval_requested') {
          setApprovalRequired(true);
          setMissionStatus('awaiting_approval');
        }

        if (event.event_type === 'approval_granted') {
          setApprovalRequired(false);
          setMissionStatus('running');
        }

        if (event.event_type === 'artifact_created' && event.details) {
          setArtifacts((prev) => [...prev, event.details]);
        }

        if (event.event_type === 'mission_completed' || event.event_type === 'mission_failed') {
          setMissionStatus(event.event_type === 'mission_completed' ? 'completed' : 'failed');
          setActiveActionIntent(undefined);
          if (event.details) {
            setReport(event.details as any as ExecutionReport);
            if (event.details.extracted_records) {
              setExtractedData(event.details.extracted_records);
            }
          }
        }
      });

      socketClientRef.current?.connectStream(mId, (b64Img: string) => {
        setScreencastFrame(b64Img);
      });

      // Poll mission state periodically if active
      const interval = setInterval(async () => {
        if (!mId) return;
        try {
          const m = await api.getMission(mId);
          if (m.status === 'awaiting_approval') {
            setMissionStatus('awaiting_approval');
            setApprovalRequired(true);
          } else if (m.status === 'running' || m.status === 'planning') {
            setMissionStatus((prev) => (prev === 'queued' ? m.status : prev));
          }

          if (m.steps && m.steps.length > 0) {
            setSteps(m.steps);
            const activeStep = m.steps.find((s: any) => s.status === 'running') || m.steps[m.steps.length - 1];
            if (activeStep?.input_value && (activeStep.action_type === 'navigate' || activeStep.action_type === 'launch_app')) {
              setCurrentUrl(activeStep.input_value);
            }
          }
          if (m.status === 'completed' || m.status === 'failed' || m.status === 'cancelled') {
            clearInterval(interval);
            setMissionStatus(m.status);
            setApprovalRequired(false);
            if (m.summary_report) {
              setReport(m.summary_report);
              setExtractedData(m.extracted_data || []);
              setArtifacts(m.artifacts || []);
            }
          }
        } catch (e) {
          clearInterval(interval);
        }
      }, 1000);
    } catch (err) {
      console.error('Mission launch failed', err);
      setMissionStatus('failed');
    }
  };

  const handleApproveStep = async () => {
    if (!activeMissionId) return;
    try {
      await api.approveMission(activeMissionId);
      setApprovalRequired(false);
    } catch (err) {
      console.error('Approval failed', err);
    }
  };

  const handleCancelMission = async () => {
    if (!activeMissionId) return;
    try {
      await api.cancelMission(activeMissionId);
      setMissionStatus('cancelled');
    } catch (err) {
      console.error('Cancellation failed', err);
    }
  };

  const selectedStep = steps.find((s) => s.step_id === selectedStepId);

  return (
    <div className="min-h-screen bg-vector-darkest text-slate-100 flex flex-col bg-grid-pattern">
      <Header
        demoMode={demoMode}
        setDemoMode={setDemoMode}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenBenchmarks={() => setIsBenchmarksOpen(true)}
        missionStatus={missionStatus}
      />

      <main className="flex-1 p-3 sm:p-6 space-y-4 sm:space-y-6 max-w-[1700px] mx-auto w-full">
        {/* Command Deck */}
        <CommandDeck
          onStartMission={handleStartMission}
          onApproveStep={handleApproveStep}
          onCancelMission={handleCancelMission}
          missionStatus={missionStatus}
          demoMode={demoMode}
          approvalRequired={approvalRequired}
        />

        {/* Primary Operational Workspace Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          {/* Left Column: Mission Execution Graph */}
          <div className="space-y-4 sm:space-y-6 flex flex-col min-w-0">
            <MissionGraph
              steps={steps}
              selectedStepId={selectedStepId}
              onSelectStep={(id) => setSelectedStepId(id)}
              missionStatus={missionStatus}
            />
            <ActionInspector step={selectedStep} />
          </div>

          {/* Right Column: Live Browser Lab Screencast & Event Stream */}
          <div className="space-y-4 sm:space-y-6 flex flex-col min-w-0">
            <BrowserLab
              currentUrl={currentUrl}
              screencastFrame={screencastFrame}
              activeAction={activeActionIntent}
              isConnected={true}
              isStreaming={missionStatus === 'running'}
            />
            <EventStream events={events} />
          </div>
        </div>

        {/* Bottom Area: Final Verification & Audit Dossier */}
        <AuditReport
          report={report}
          extractedData={extractedData}
          artifacts={artifacts}
          missionId={activeMissionId || undefined}
        />
      </main>

      {/* Settings Modal */}
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

      {/* Benchmark 20 Suite Modal */}
      <BenchmarkModal isOpen={isBenchmarksOpen} onClose={() => setIsBenchmarksOpen(false)} />
    </div>
  );
};

export default App;
