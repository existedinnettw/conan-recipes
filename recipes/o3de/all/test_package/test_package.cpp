#include <AzCore/Memory/SystemAllocator.h>
#include <AzCore/Math/Vector3.h>
#include <AzCore/RTTI/RTTI.h>
#include <AzCore/Serialization/SerializeContext.h>
#include <AzCore/Serialization/Json/JsonSerialization.h>
#include <AzCore/Serialization/Json/JsonSystemComponent.h>
#include <AzCore/Serialization/Json/RegistrationContext.h>
#include <AzCore/JSON/document.h>
#include <AzCore/JSON/stringbuffer.h>
#include <AzCore/JSON/writer.h>
#include <AzCore/std/string/string.h>
#include <AzNetworking/Utilities/IpAddress.h>
#include <AzFramework/Input/Channels/InputChannelId.h>
#if defined(O3DE_TEST_ATOM)
#include <Atom/RHI.Reflect/Format.h>
#endif
#if defined(O3DE_TEST_EDITOR)
#include <AzQtComponents/Utilities/Conversions.h>
#include <AzToolsFramework/API/ToolsApplicationAPI.h>
#endif
#if defined(O3DE_TEST_GEM_MODULES)
#include <AzCore/Module/Module.h>

// AZ_DECLARE_MODULE_CLASS in a monolithic build
extern "C" AZ::Module* CreateModuleClass_Gem_Atom_RPI_Private();
#endif

#include <cstdio>

struct Pose
{
    AZ_TYPE_INFO(Pose, "{6A1D5C33-6E35-4C4B-9A43-1C8C3B5F2E10}");

    AZ::Vector3 m_position = AZ::Vector3::CreateZero();
    float m_yaw = 0.0f;

    static void Reflect(AZ::SerializeContext& context)
    {
        context.Class<Pose>()->Field("position", &Pose::m_position)->Field("yaw", &Pose::m_yaw);
    }
};

int main()
{
    AZ::AllocatorInstance<AZ::SystemAllocator>::Get();
    int result = 0;
    {
        AZ::SerializeContext serializeContext;
        AZ::JsonRegistrationContext jsonContext;
        AZ::JsonSystemComponent::Reflect(&jsonContext);
        Pose::Reflect(serializeContext);

        Pose pose;
        pose.m_position = AZ::Vector3(1.0f, 2.0f, 3.0f).GetNormalized() * 2.0f;
        pose.m_yaw = 0.5f;

        AZ::JsonSerializerSettings settings;
        settings.m_serializeContext = &serializeContext;
        settings.m_registrationContext = &jsonContext;
        rapidjson::Document document;
        AZ::JsonSerialization::Store(document, document.GetAllocator(), pose, settings);
        rapidjson::StringBuffer buffer;
        rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
        document.Accept(writer);
        std::printf("Pose as JSON: %s\n", buffer.GetString());

        AzNetworking::IpAddress address("127.0.0.1", 33450, AzNetworking::ProtocolType::Udp);
        std::printf("Address: %s\n", address.GetString().c_str());

        AzFramework::InputChannelId channel("keyboard_key_alphanumeric_A");
        std::printf("Input channel: %s\n", channel.GetName());

        result = (AZStd::string(buffer.GetString()).find("yaw") == AZStd::string::npos) ? 1 : 0;

#if defined(O3DE_TEST_ATOM)
        std::printf("Atom RHI format: %s, %u bytes per pixel\n", AZ::RHI::ToString(AZ::RHI::Format::R8G8B8A8_UNORM),
                    AZ::RHI::GetFormatSize(AZ::RHI::Format::R8G8B8A8_UNORM));
        result |= AZ::RHI::GetFormatSize(AZ::RHI::Format::R8G8B8A8_UNORM) == 4 ? 0 : 1;
#endif
#if defined(O3DE_TEST_GEM_MODULES)
        AZ::Module* rpiModule = CreateModuleClass_Gem_Atom_RPI_Private();
        std::printf("Atom RPI Gem module: %zu system components\n", rpiModule->GetRequiredSystemComponents().size());
        result |= rpiModule->GetRequiredSystemComponents().empty() ? 1 : 0;
        delete rpiModule;
#endif
#if defined(O3DE_TEST_EDITOR)
        const QColor color = AzQtComponents::toQColor(AZ::Color(1.0f, 0.5f, 0.0f, 1.0f));
        std::printf("AzQtComponents color: %s\n", color.name().toUtf8().constData());
        result |= color.red() == 255 ? 0 : 1;
#endif
        // Reflection contexts must be emptied before they are destroyed.
        serializeContext.EnableRemoveReflection();
        Pose::Reflect(serializeContext);
        serializeContext.DisableRemoveReflection();
        jsonContext.EnableRemoveReflection();
        AZ::JsonSystemComponent::Reflect(&jsonContext);
        jsonContext.DisableRemoveReflection();
    }
    return result;
}
